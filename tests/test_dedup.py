"""Safe same-name image deduplication and native copy-on-write behavior."""

import errno
import os
import sys
import tempfile
from pathlib import Path

import pytest

from clearml_yolo.adapters.storage import dedup


def pair(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "a" / "image.jpg"
    destination = tmp_path / "b" / "image.jpg"
    source.parent.mkdir()
    destination.parent.mkdir()
    source.write_bytes(b"identical image bytes")
    destination.write_bytes(source.read_bytes())
    return source, destination


def copy_clone(source_fd: int, destination_fd: int) -> None:
    """Exercise replacement independently of filesystem reflink support."""
    while chunk := os.read(source_fd, 1024):
        os.write(destination_fd, chunk)


@pytest.fixture
def simulated_clone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dedup, "_clone", copy_clone)


def test_only_identical_same_names_are_candidates(tmp_path: Path) -> None:
    pair(tmp_path)
    (tmp_path / "other.jpg").write_bytes(b"identical image bytes")
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "image.jpg").write_bytes(b"different image bytes")
    (tmp_path / "notes.txt").write_bytes(b"identical image bytes")
    result = dedup.deduplicate(tmp_path, dry_run=True)
    assert (result.scanned, result.duplicates, result.reflinked, result.failures) == (4, 1, 0, 0)


def test_dry_run_creates_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, destination = pair(tmp_path)
    before = destination.stat()

    def forbidden_clone(_source_fd: int, _destination_fd: int) -> None:
        pytest.fail("dry run attempted cloning")

    monkeypatch.setattr(dedup, "_clone", forbidden_clone)
    result = dedup.deduplicate(tmp_path, dry_run=True)
    assert result.duplicates == 1
    assert result.reflinked == 0
    assert destination.stat() == before
    assert sorted(destination.parent.iterdir()) == [destination]
    assert source.read_bytes() == destination.read_bytes()


def test_replacement_preserves_destination_metadata(tmp_path: Path, simulated_clone: None) -> None:
    source, destination = pair(tmp_path)
    destination.chmod(0o640)
    os.utime(destination, ns=(1_600_000_000_000_000_000, 1_610_000_000_000_000_000))
    os.setxattr(destination, "user.dedup-test", b"destination metadata")
    before = destination.stat()
    result = dedup.deduplicate(tmp_path)
    after = destination.stat()
    assert (result.reflinked, result.failures) == (1, 0)
    assert after.st_ino != before.st_ino
    assert (after.st_mode, after.st_uid, after.st_gid) == (
        before.st_mode,
        before.st_uid,
        before.st_gid,
    )
    assert (after.st_atime_ns, after.st_mtime_ns) == (before.st_atime_ns, before.st_mtime_ns)
    assert os.getxattr(destination, "user.dedup-test") == b"destination metadata"
    destination.write_bytes(b"independent update")
    assert source.read_bytes() == b"identical image bytes"


def test_symlinks_and_hardlink_aliases_are_not_replaced(tmp_path: Path) -> None:
    source, destination = pair(tmp_path)
    destination.unlink()
    destination.hardlink_to(source)
    (tmp_path / "linked.jpg").symlink_to(source)
    (tmp_path / "nested").symlink_to(source.parent, target_is_directory=True)
    result = dedup.deduplicate(tmp_path)
    assert result.scanned == 2
    assert result.reflinked == 0
    assert result.skipped >= 1
    assert destination.stat().st_ino == source.stat().st_ino
    with pytest.raises(ValueError, match="symlink"):
        dedup.deduplicate(tmp_path / "nested")


@pytest.mark.parametrize("error", [errno.EOPNOTSUPP, errno.ENOTTY, errno.EXDEV])
def test_unsupported_clone_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: int
) -> None:
    _, destination = pair(tmp_path)
    before = destination.stat()

    fcntl = pytest.importorskip("fcntl")

    def unsupported(_destination_fd: int, _operation: int, _source_fd: int) -> None:
        raise OSError(error, "reflink unavailable")

    monkeypatch.setattr(fcntl, "ioctl", unsupported)
    result = dedup.deduplicate(tmp_path)
    assert (result.duplicates, result.skipped, result.failures, result.reflinked) == (1, 1, 0, 0)
    assert result.issues
    assert destination.stat().st_ino == before.st_ino
    assert destination.read_bytes() == b"identical image bytes"
    assert list(destination.parent.iterdir()) == [destination]


def test_permission_failure_keeps_original(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, destination = pair(tmp_path)
    before = destination.stat()

    def denied(_source_fd: int, _destination_fd: int) -> None:
        raise PermissionError(errno.EACCES, "permission denied")

    monkeypatch.setattr(dedup, "_clone", denied)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert destination.stat().st_ino == before.st_ino
    assert list(destination.parent.iterdir()) == [destination]


def test_metadata_failure_keeps_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, simulated_clone: None
) -> None:
    _, destination = pair(tmp_path)
    before = destination.stat()

    def denied(_fd: int, _mode: int) -> None:
        raise PermissionError(errno.EPERM, "metadata denied")

    monkeypatch.setattr(os, "fchmod", denied)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert destination.stat().st_ino == before.st_ino
    assert list(destination.parent.iterdir()) == [destination]


def test_intervening_destination_write_is_not_lost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, destination = pair(tmp_path)

    def racing_clone(source_fd: int, destination_fd: int) -> None:
        copy_clone(source_fd, destination_fd)
        destination.write_bytes(b"new concurrent data")

    monkeypatch.setattr(dedup, "_clone", racing_clone)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert destination.read_bytes() == b"new concurrent data"
    assert list(destination.parent.iterdir()) == [destination]


def test_interruption_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, destination = pair(tmp_path)

    def interrupted(_source_fd: int, _destination_fd: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(dedup, "_clone", interrupted)
    with pytest.raises(KeyboardInterrupt):
        dedup.deduplicate(tmp_path)
    assert destination.read_bytes() == b"identical image bytes"
    assert list(destination.parent.iterdir()) == [destination]


def test_native_reflink_independent_write(tmp_path: Path) -> None:
    source, destination = pair(tmp_path)
    result = dedup.deduplicate(tmp_path)
    if result.skipped:
        pytest.skip("Native reflink unsupported: " + "; ".join(result.issues))
    assert result.failures == 0, result.issues
    assert result.reflinked == 1
    assert destination.stat().st_ino != source.stat().st_ino
    destination.write_bytes(b"modified destination")
    assert source.read_bytes() == b"identical image bytes"


def test_hash_collision_never_replaces_different_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, destination = pair(tmp_path)
    destination.write_bytes(b"different image bytes")
    assert source.stat().st_size == destination.stat().st_size
    monkeypatch.setattr(dedup, "_digest", lambda _file: b"collision")
    before = destination.stat()
    result = dedup.deduplicate(tmp_path)
    assert result.duplicates == 0
    assert destination.stat().st_ino == before.st_ino
    assert destination.read_bytes() == b"different image bytes"


def test_cross_device_candidate_does_not_prevent_same_device_dedup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, simulated_clone: None
) -> None:
    source, destination = pair(tmp_path)
    third = tmp_path / "c" / "image.jpg"
    third.parent.mkdir()
    third.write_bytes(source.read_bytes())
    source_stat = source.stat()
    changed_stat = os.stat_result(
        (
            source_stat.st_mode,
            source_stat.st_ino,
            source_stat.st_dev + 1,
            source_stat.st_nlink,
            source_stat.st_uid,
            source_stat.st_gid,
            source_stat.st_size,
            source_stat.st_atime,
            source_stat.st_mtime,
            source_stat.st_ctime,
        )
    )
    original_scan = dedup._scan

    def cross_device_scan(directory: Path, result: dedup.DedupResult) -> list[dedup._File]:
        return [
            dedup._File(file.path, changed_stat) if file.path == source else file
            for file in original_scan(directory, result)
        ]

    monkeypatch.setattr(dedup, "_scan", cross_device_scan)
    monkeypatch.setattr(dedup, "_digest", lambda _file: b"identical")
    monkeypatch.setattr(dedup, "_equal", lambda _source, _destination: True)
    result = dedup.deduplicate(tmp_path)
    assert (result.duplicates, result.skipped, result.reflinked, result.failures) == (2, 1, 1, 0)
    assert destination.read_bytes() == third.read_bytes()


def test_unsupported_platform_does_not_mutate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, destination = pair(tmp_path)
    before = destination.stat()
    monkeypatch.setattr(sys, "platform", "win32")
    result = dedup.deduplicate(tmp_path)
    assert (result.skipped, result.failures, result.reflinked) == (1, 0, 0)
    assert destination.stat().st_ino == before.st_ino


def test_read_permission_error_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, destination = pair(tmp_path)
    original_open = os.open

    def denied(path: Path, flags: int) -> int:
        if path == destination:
            raise PermissionError(errno.EACCES, "unreadable image", str(path))
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", denied)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert result.issues
    assert destination.read_bytes() == b"identical image bytes"


def test_intervening_source_write_prevents_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, destination = pair(tmp_path)
    before = destination.stat()

    def racing_clone(source_fd: int, destination_fd: int) -> None:
        copy_clone(source_fd, destination_fd)
        source.write_bytes(b"changed source")

    monkeypatch.setattr(dedup, "_clone", racing_clone)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert destination.stat().st_ino == before.st_ino
    assert destination.read_bytes() == b"identical image bytes"
    assert list(destination.parent.iterdir()) == [destination]


def test_case_sensitive_basename_and_case_insensitive_extension(tmp_path: Path) -> None:
    source, _ = pair(tmp_path)
    (tmp_path / "b" / "IMAGE.JPG").write_bytes(source.read_bytes())
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "IMAGE.JPG").write_bytes(source.read_bytes())
    result = dedup.deduplicate(tmp_path, dry_run=True)
    assert (result.scanned, result.duplicates) == (4, 2)


@pytest.mark.parametrize("corrupt_content", [b"incomplete", b"corrupted image bytes"])
def test_incomplete_clone_never_replaces_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt_content: bytes
) -> None:
    _, destination = pair(tmp_path)
    before = destination.stat()

    def incomplete(_source_fd: int, destination_fd: int) -> None:
        os.write(destination_fd, corrupt_content)

    monkeypatch.setattr(dedup, "_clone", incomplete)
    result = dedup.deduplicate(tmp_path)
    assert result.failures == 1
    assert result.reflinked == 0
    assert destination.stat().st_ino == before.st_ino
    assert destination.read_bytes() == b"identical image bytes"
    assert list(destination.parent.iterdir()) == [destination]


def test_unsupported_platform_skips_before_temporary_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair(tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")

    def forbidden(*_args: object, **_kwargs: object) -> tuple[int, str]:
        pytest.fail("unsupported platform attempted creating a temporary file")

    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    result = dedup.deduplicate(tmp_path)
    assert (result.skipped, result.failures) == (1, 0)


def test_multi_chunk_content_difference_is_not_deduplicated(tmp_path: Path) -> None:
    source, destination = pair(tmp_path)
    prefix = b"x" * (2 * 1024 * 1024)
    source.write_bytes(prefix + b"a")
    destination.write_bytes(prefix + b"b")
    result = dedup.deduplicate(tmp_path)
    assert result.duplicates == 0
    destination.write_bytes(prefix + b"a")
    result = dedup.deduplicate(tmp_path, dry_run=True)
    assert result.duplicates == 1
