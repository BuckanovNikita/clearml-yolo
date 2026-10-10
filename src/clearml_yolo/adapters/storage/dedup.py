"""Deduplicate same-name images using atomic, metadata-preserving Linux reflinks.

The cache must be idle. Stat checks detect ordinary intervening writes, but this
utility does not provide synchronization against adversarial filesystem races.
"""

import errno
import hashlib
import os
import stat
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from clearml_yolo.adapters.observability.tracing import trace_operation

IMAGE_EXTENSIONS = frozenset(
    {".bmp", ".dng", ".jpeg", ".jpg", ".mpo", ".png", ".tif", ".tiff", ".webp", ".pfm", ".heic"}
)
_CHUNK_SIZE = 1024 * 1024
_FICLONE = 0x40049409
_UNSUPPORTED_ERRNOS = {errno.EOPNOTSUPP, errno.ENOTTY, errno.EXDEV, errno.EINVAL, errno.ENOSYS}


@dataclass
class DedupResult:
    """Image counts; duplicate candidates include skipped and failed replacements."""

    scanned: int = 0
    duplicates: int = 0
    reflinked: int = 0
    skipped: int = 0
    failures: int = 0
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _File:
    path: Path
    snapshot: os.stat_result


class _UnsupportedError(OSError):
    """The required reflink operation is unavailable; never fall back to copying."""


def _identity(snapshot: os.stat_result) -> tuple[int, ...]:
    # Reading can update atime, so it is intentionally absent from change detection.
    return (
        snapshot.st_dev,
        snapshot.st_ino,
        snapshot.st_size,
        snapshot.st_mtime_ns,
        snapshot.st_ctime_ns,
        snapshot.st_mode,
        snapshot.st_uid,
        snapshot.st_gid,
        snapshot.st_nlink,
    )


def _check(file: _File, snapshot: os.stat_result) -> None:
    if _identity(snapshot) != _identity(file.snapshot):
        raise OSError(errno.EBUSY, "file changed during deduplication", str(file.path))


@contextmanager
def _open(file: _File) -> Iterator[BinaryIO]:
    descriptor = os.open(file.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        _check(file, os.fstat(stream.fileno()))
        yield stream


@trace_operation("storage.dedup.scan")
def _scan(directory: Path, result: DedupResult) -> list[_File]:
    files: list[_File] = []
    pending = [directory]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        snapshot = entry.stat(follow_symlinks=False)
                        path = Path(entry.path)
                        if stat.S_ISDIR(snapshot.st_mode):
                            pending.append(path)
                        elif (
                            stat.S_ISREG(snapshot.st_mode)
                            and path.suffix.lower() in IMAGE_EXTENSIONS
                        ):
                            files.append(_File(path, snapshot))
                            result.scanned += 1
                    except OSError as error:
                        _failure(result, Path(entry.path), error)
        except OSError as error:
            _failure(result, current, error)
    return sorted(files, key=lambda file: str(file.path))


def _failure(result: DedupResult, path: Path, error: OSError) -> None:
    result.failures += 1
    result.issues.append(f"Failed {path}: {error}")


def _digest(file: _File) -> bytes:
    digest = hashlib.sha256()
    with _open(file) as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            digest.update(chunk)
        _check(file, os.fstat(stream.fileno()))
    return digest.digest()


def _equal(source: _File, destination: _File) -> bool:
    with _open(source) as left, _open(destination) as right:
        while True:
            chunk = left.read(_CHUNK_SIZE)
            other = right.read(_CHUNK_SIZE)
            if chunk != other or not chunk:
                _check(source, os.fstat(left.fileno()))
                _check(destination, os.fstat(right.fileno()))
                return chunk == other


def _candidates(files: list[_File], result: DedupResult) -> Iterator[tuple[_File, _File]]:
    groups: dict[tuple[str, int], list[_File]] = defaultdict(list)
    for file in files:
        groups[file.path.name, file.snapshot.st_size].append(file)
    for group in groups.values():
        if len(group) == 1:
            continue
        by_digest: dict[bytes, list[_File]] = defaultdict(list)
        for file in group:
            try:
                digest = _digest(file)
                sources = sorted(
                    by_digest[digest],
                    key=lambda source: source.snapshot.st_dev != file.snapshot.st_dev,
                )
                for source in sources:
                    if _equal(source, file):
                        yield source, file
                        if source.snapshot.st_dev != file.snapshot.st_dev:
                            by_digest[digest].append(file)
                        break
                else:
                    by_digest[digest].append(file)
            except OSError as error:
                _failure(result, file.path, error)


def _clone(source_fd: int, destination_fd: int) -> None:
    if sys.platform != "linux":
        raise _UnsupportedError(errno.ENOSYS, "reflinks require Linux FICLONE")
    import fcntl

    try:
        fcntl.ioctl(destination_fd, _FICLONE, source_fd)
    except OSError as error:
        if error.errno in _UNSUPPORTED_ERRNOS:
            raise _UnsupportedError(error.errno, "filesystem does not support FICLONE") from error
        raise


def _metadata(destination: _File, original_fd: int, temporary_fd: int) -> None:
    snapshot = destination.snapshot
    temporary_stat = os.fstat(temporary_fd)
    if (temporary_stat.st_uid, temporary_stat.st_gid) != (snapshot.st_uid, snapshot.st_gid):
        os.fchown(temporary_fd, snapshot.st_uid, snapshot.st_gid)
    os.fchmod(temporary_fd, stat.S_IMODE(snapshot.st_mode))
    # Sibling creation may inherit ACLs or other xattrs; preserve the destination's exact set.
    original_attributes = set(os.listxattr(original_fd))
    for name in os.listxattr(temporary_fd):
        if name not in original_attributes:
            os.removexattr(temporary_fd, name)
    for name in original_attributes:
        os.setxattr(temporary_fd, name, os.getxattr(original_fd, name))
    os.utime(temporary_fd, ns=(snapshot.st_atime_ns, snapshot.st_mtime_ns))


def _verify_clone(source_fd: int, temporary_fd: int) -> None:
    if os.fstat(source_fd).st_size != os.fstat(temporary_fd).st_size:
        raise OSError(errno.EIO, "cloned image size does not match source")
    offset = 0
    while chunk := os.pread(source_fd, _CHUNK_SIZE, offset):
        if chunk != os.pread(temporary_fd, _CHUNK_SIZE, offset):
            raise OSError(errno.EIO, "cloned image bytes do not match source")
        offset += len(chunk)


def _replace(source: _File, destination: _File) -> None:
    if sys.platform != "linux":
        raise _UnsupportedError(errno.ENOSYS, "reflinks require Linux FICLONE")
    with _open(source) as source_stream, _open(destination) as destination_stream:
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=".cy-dedup-", dir=destination.path.parent
        )
        temporary = Path(temporary_name)
        try:
            _clone(source_stream.fileno(), temporary_fd)
            _verify_clone(source_stream.fileno(), temporary_fd)
            _metadata(destination, destination_stream.fileno(), temporary_fd)
            os.fsync(temporary_fd)
            for file, descriptor in (
                (source, source_stream.fileno()),
                (destination, destination_stream.fileno()),
            ):
                _check(file, os.fstat(descriptor))
                _check(file, file.path.lstat())
            temporary.replace(destination.path)
        finally:
            os.close(temporary_fd)
            temporary.unlink(missing_ok=True)


@trace_operation("storage.dedup")
def deduplicate(directory: Path, *, dry_run: bool = False) -> DedupResult:
    """Reflink byte-identical regular images sharing an exact basename.

    Dry runs only count duplicates; they cannot establish filesystem reflink support.
    Failures and unsupported operations retain originals and are reported in the result.
    Symlinks are excluded. Invalid roots raise ValueError or OSError.
    """
    root_stat = directory.lstat()
    if stat.S_ISLNK(root_stat.st_mode):
        raise ValueError(f"Directory must not be a symlink: {directory}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise NotADirectoryError(errno.ENOTDIR, "expected a directory", str(directory))
    result = DedupResult()
    for source, destination in _candidates(_scan(directory, result), result):
        result.duplicates += 1
        if destination.snapshot.st_nlink > 1:
            result.skipped += 1
            result.issues.append(f"Skipped existing hardlink: {destination.path}")
        elif source.snapshot.st_dev != destination.snapshot.st_dev:
            result.skipped += 1
            result.issues.append(f"Skipped cross-device duplicate: {destination.path}")
        elif not dry_run:
            try:
                _replace(source, destination)
            except _UnsupportedError as error:
                result.skipped += 1
                result.issues.append(f"Skipped unsupported reflink {destination.path}: {error}")
            except OSError as error:
                _failure(result, destination.path, error)
            else:
                result.reflinked += 1
    return result
