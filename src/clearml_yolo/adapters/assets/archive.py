"""Verify and extract the approved DEIM source without executing archive content."""

import hashlib
import json
import shutil
import tarfile
import tempfile
from importlib.resources import files
from pathlib import Path, PurePosixPath

from clearml_yolo.adapters.storage.filesystem import write_path

_MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
_MAX_MEMBERS = 5000


def source_manifest() -> dict[str, str]:
    raw: object = json.loads(
        files("clearml_yolo.adapters.assets").joinpath("deim-manifest.json").read_text()
    )
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise TypeError("Packaged DEIM source manifest is invalid")
    return dict(raw)


def _members(archive: tarfile.TarFile) -> list[tuple[tarfile.TarInfo, str]]:
    result: list[tuple[tarfile.TarInfo, str]] = []
    roots: set[str] = set()
    names: set[str] = set()
    total = 0
    for member in archive:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name:
            raise ValueError(f"Unsafe DEIM archive path: {member.name}")
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"Unsupported DEIM archive member: {member.name}")
        if not path.parts:
            raise ValueError("Empty DEIM archive path")
        roots.add(path.parts[0])
        relative = str(PurePosixPath(*path.parts[1:]))
        if member.isfile():
            if relative in names or len(path.parts) <= 1:
                raise ValueError(f"Duplicate or uncontained DEIM archive member: {member.name}")
            names.add(relative)
            total += member.size
            result.append((member, relative))
        if len(names) > _MAX_MEMBERS or total > _MAX_ARCHIVE_BYTES:
            raise ValueError("DEIM source archive exceeds its bounded source inventory")
    if len(roots) != 1:
        raise ValueError("DEIM source archive must have one top-level directory")
    return result


def validate_archive(path: Path) -> None:
    manifest = source_manifest()
    found: dict[str, str] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member, relative in _members(archive):
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"Unreadable DEIM archive member: {relative}")
            with stream:
                found[relative] = hashlib.sha256(stream.read()).hexdigest()
    if found != manifest:
        raise ValueError("DEIM source archive contents differ from the approved manifest")


def validate_source(path: Path) -> None:
    manifest = source_manifest()
    found: dict[str, str] = {}
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"DEIM source directory is missing or unsafe: {path}")
    for item in path.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"DEIM source contains a symbolic link: {item}")
        if item.is_file():
            relative = item.relative_to(path)
            # Native Python imports create bytecode caches; source loading ignores
            # them and always compiles the verified source (see deim.source).
            if "__pycache__" in relative.parts and item.suffix == ".pyc":
                continue
            with item.open("rb") as stream:
                found[relative.as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    if found != manifest:
        raise ValueError("DEIM source contents differ from the approved manifest")


def extract_source(archive_path: Path, destination: Path) -> Path:
    destination = write_path(destination)
    if destination.exists():
        validate_source(destination)
        return destination
    validate_archive(archive_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".deim-extract-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "source"
        staging.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            for member, relative in _members(archive):
                output = staging / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Unreadable DEIM archive member: {relative}")
                with stream, output.open("xb") as target:
                    shutil.copyfileobj(stream, target)
        validate_source(staging)
        staging.rename(destination)
    return destination
