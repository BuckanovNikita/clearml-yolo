"""Checkpoint-byte hashing and durable model identity sidecars."""

import hashlib
from pathlib import Path

from clearml_yolo.core.identity import ModelIdentity


def checkpoint_sha256(path: Path) -> str:
    """Hash actual checkpoint bytes with bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_checkpoint_identity(path: Path, identity: ModelIdentity) -> Path:
    """Persist checkpoint identity beside local weights after checking their bytes."""
    actual_hash = checkpoint_sha256(path)
    if identity.checkpoint_sha256 != actual_hash:
        raise ValueError("Checkpoint identity does not match local checkpoint bytes")
    sidecar = path.with_name(path.name + ".identity.json")
    sidecar.write_text(identity.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return sidecar

def read_checkpoint_identity(path: Path) -> ModelIdentity | None:
    """Recover a local checkpoint's known source, rejecting stale association."""
    sidecar = path.with_name(path.name + ".identity.json")
    if not sidecar.is_file():
        return None
    identity = ModelIdentity.model_validate_json(sidecar.read_text(encoding="utf-8"))
    if identity.checkpoint_sha256 != checkpoint_sha256(path):
        raise ValueError("Stored checkpoint identity does not match local checkpoint bytes")
    return identity
