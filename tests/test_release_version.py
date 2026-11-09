"""The release build step patches only the root uv.lock version, byte for byte."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts import release_version

PYPROJECT = b"""[project]
name = "clearml-yolo"
version = "0.4.0"
dependencies = ["dep>=1"]

[tool.semantic_release]
tag_format = "v{version}"
"""
LOCK = b"""version = 1
revision = 3

[[package]]
name = "clearml-yolo"
version = "0.4.0"
source = { editable = "." }
dependencies = [
    { name = "dep" },
]

[package.metadata]
requires-dist = [{ name = "dep", specifier = ">=1" }]

[[package]]
name = "dep"
version = "0.4.0"
source = { registry = "https://pypi.org/simple" }
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed Git arguments in a test-owned repository
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "master")
    (tmp_path / "pyproject.toml").write_bytes(PYPROJECT)
    (tmp_path / "uv.lock").write_bytes(LOCK)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def _bump(repo: Path, version: str = "0.5.0") -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT.replace(b'version = "0.4.0"', f'version = "{version}"'.encode()))


def test_patches_only_the_root_package_version(repo: Path) -> None:
    _bump(repo)

    assert release_version.patch_lock(repo, "0.5.0") is True
    expected = LOCK.replace(b'clearml-yolo"\nversion = "0.4.0"', b'clearml-yolo"\nversion = "0.5.0"')
    assert (repo / "uv.lock").read_bytes() == expected


def test_repeated_run_keeps_the_patched_lock(repo: Path) -> None:
    _bump(repo)
    release_version.patch_lock(repo)
    patched = (repo / "uv.lock").read_bytes()

    assert release_version.patch_lock(repo) is False
    assert (repo / "uv.lock").read_bytes() == patched


def test_announced_version_must_match_pyproject(repo: Path) -> None:
    _bump(repo)

    with pytest.raises(release_version.ReleaseVersionError, match=r"announced 0\.6\.0"):
        release_version.patch_lock(repo, "0.6.0")


def test_source_override_in_pyproject_blocks_release(repo: Path) -> None:
    _bump(repo)
    with (repo / "pyproject.toml").open("ab") as stream:
        stream.write(b'\n[tool.uv.sources]\ndep = { path = "external/dep" }\n')

    with pytest.raises(release_version.ReleaseVersionError, match=r"beyond project\.version"):
        release_version.patch_lock(repo)


def test_drifted_lock_blocks_release(repo: Path) -> None:
    _bump(repo)
    (repo / "uv.lock").write_bytes(LOCK.replace(b"revision = 3", b"revision = 4"))

    with pytest.raises(release_version.ReleaseVersionError, match="differs from HEAD"):
        release_version.patch_lock(repo)


def test_lock_root_must_be_the_editable_project(repo: Path) -> None:
    (repo / "uv.lock").write_bytes(LOCK.replace(b'{ editable = "." }', b'{ virtual = "." }'))
    _git(repo, "commit", "-q", "-am", "virtual root")
    _bump(repo)

    with pytest.raises(release_version.ReleaseVersionError, match="source editable"):
        release_version.patch_lock(repo)


def test_lock_root_must_match_head_project_version(repo: Path) -> None:
    (repo / "uv.lock").write_bytes(
        LOCK.replace(b'clearml-yolo"\nversion = "0.4.0"', b'clearml-yolo"\nversion = "0.3.0"')
    )
    _git(repo, "commit", "-q", "-am", "stale lock")
    _bump(repo)

    with pytest.raises(release_version.ReleaseVersionError, match=r"differs from HEAD 0\.4\.0"):
        release_version.patch_lock(repo)


def test_non_release_version_is_refused(repo: Path) -> None:
    _bump(repo, "0.5.0rc1")

    with pytest.raises(release_version.ReleaseVersionError, match="unexpected release version"):
        release_version.patch_lock(repo)


def test_committed_project_lock_changes_exactly_one_line() -> None:
    lock = subprocess.run(  # noqa: S603 - read-only Git query
        ["git", "-C", str(ROOT), "show", "HEAD:uv.lock"],  # noqa: S607 - Git from PATH
        check=True,
        capture_output=True,
    ).stdout

    patched = release_version.version_bytes(lock, "999.0.0", lock=True, name="clearml-yolo")

    changed = [
        (before, after)
        for before, after in zip(lock.splitlines(), patched.splitlines(), strict=True)
        if before != after
    ]
    assert len(changed) == 1
    assert changed[0][1] == b'version = "999.0.0"'
