"""Portable export provenance and TensorRT optimization profiles."""

import hashlib
from pathlib import Path

from clearml_yolo.core.export import ExportMetadata


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_metadata(metadata: ExportMetadata, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")


def read_metadata(path: Path) -> ExportMetadata:
    return ExportMetadata.model_validate_json(path.read_text(encoding="utf-8"))
