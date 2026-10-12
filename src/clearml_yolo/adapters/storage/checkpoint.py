"""Bind portable detector metadata to native Torch archives without importing Torch."""

import json
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile, ZipFile, is_zipfile

from clearml_yolo.adapters.storage.identity import checkpoint_sha256
from clearml_yolo.core.models import CheckpointDescriptor, CheckpointMetadata, ModelConfig

_METADATA_NAME = "detector_metadata.json"
_MAX_METADATA_BYTES = 256 * 1024


def _member(archive: ZipFile) -> str:
    roots = [
        name.removesuffix("data.pkl") for name in archive.namelist() if name.endswith("/data.pkl")
    ]
    if len(roots) != 1:
        raise ValueError("Checkpoint must contain one native Torch archive root")
    return roots[0] + _METADATA_NAME


def _embedded(path: Path) -> CheckpointMetadata | None:
    if not is_zipfile(path):
        return None
    try:
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.endswith("/" + _METADATA_NAME)]
            if not members:
                return None
            if len(members) != 1 or members[0] != _member(archive):
                raise ValueError("Checkpoint contains ambiguous detector metadata")
            info = archive.getinfo(members[0])
            if info.file_size > _MAX_METADATA_BYTES:
                raise ValueError("Checkpoint detector metadata exceeds the size limit")
            return CheckpointMetadata.model_validate_json(archive.read(info))
    except BadZipFile as error:
        raise ValueError("Checkpoint archive is corrupt") from error


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".model.json")


def _write_descriptor(path: Path, descriptor: CheckpointDescriptor) -> None:
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(descriptor.model_dump_json(indent=2) + "\n")
        temporary.replace(_sidecar(path))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_checkpoint_descriptor(
    path: Path, *, expected: ModelConfig | None = None
) -> CheckpointDescriptor | None:
    """Read checkpoint-owned classes and validate optional hash/selection assertions."""
    metadata = _embedded(path)
    sidecar = _sidecar(path)
    if metadata is None:
        if sidecar.is_file():
            raise ValueError("Descriptor sidecar has no corresponding checkpoint metadata")
        return None
    digest = checkpoint_sha256(path)
    descriptor = CheckpointDescriptor(**metadata.model_dump(), checkpoint_sha256=digest)
    if sidecar.is_file():
        recorded = CheckpointDescriptor.model_validate_json(sidecar.read_text(encoding="utf-8"))
        if recorded.checkpoint_sha256 != digest:
            raise ValueError("Checkpoint hash disagrees with its stored descriptor")
        if recorded != descriptor:
            raise ValueError("Descriptor metadata disagrees with the checkpoint")
    if expected is not None and (expected.backend, expected.preset) != (
        descriptor.backend,
        descriptor.preset,
    ):
        raise ValueError("Explicit model selection disagrees with the checkpoint descriptor")
    return descriptor


def bind_checkpoint(path: Path, metadata: CheckpointMetadata) -> CheckpointDescriptor:
    """Atomically annotate an owned checkpoint; native Torch readers ignore extra records."""
    if path.is_symlink():
        raise ValueError("Refusing to modify a checkpoint symlink")
    existing = read_checkpoint_descriptor(path)
    if existing is not None:
        values = existing.model_dump(exclude={"checkpoint_sha256"})
        if CheckpointMetadata.model_validate(values) != metadata:
            raise ValueError("Checkpoint already has different detector metadata")
        return existing
    encoded = json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > _MAX_METADATA_BYTES:
        raise ValueError("Checkpoint detector metadata exceeds the size limit")
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
        shutil.copyfile(path, temporary)
        with ZipFile(temporary, "a") as archive:
            archive.writestr(_member(archive), encoded)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    descriptor = CheckpointDescriptor(
        **metadata.model_dump(), checkpoint_sha256=checkpoint_sha256(path)
    )
    _write_descriptor(path, descriptor)
    return descriptor
