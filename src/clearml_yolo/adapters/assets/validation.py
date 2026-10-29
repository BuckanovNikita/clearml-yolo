"""Content validation shared by URL and native Hub cache publication."""

import hashlib
import zipfile
from pathlib import Path

from safetensors import SafetensorError, safe_open

from clearml_yolo.adapters.assets.archive import validate_archive
from clearml_yolo.core.assets import AssetSpec


def _safetensors(path: Path) -> None:
    try:
        with safe_open(path, framework="numpy") as tensors:
            if not tensors.keys():
                raise ValueError("Safetensors asset contains no tensors")
    except SafetensorError as error:
        raise ValueError("Invalid safetensors asset") from error


def validate_asset(path: Path, spec: AssetSpec) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Asset is missing or empty")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if spec.checksum:
        actual = digest
        if spec.checksum_algorithm == "md5":
            with path.open("rb") as stream:
                actual = hashlib.file_digest(
                    stream, lambda: hashlib.md5(usedforsecurity=False)
                ).hexdigest()
        if not actual.startswith(spec.checksum.lower()):
            raise ValueError(f"Asset {spec.checksum_algorithm} checksum mismatch")
    if spec.kind == "deim-source":
        validate_archive(path)
    elif spec.filename.endswith(".safetensors"):
        _safetensors(path)
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or not any(
                name.endswith("/data.pkl") for name in archive.namelist()
            ):
                raise ValueError("Invalid native Torch checkpoint archive")
    else:
        with path.open("rb") as stream:
            prefix = stream.read(16)
        # Legacy Torch serialization begins with its pickled magic integer. Loading
        # and native shape validation remain backend responsibilities, using safe loaders.
        if not prefix.startswith(b"\x80\x02\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19"):
            raise ValueError("Asset is not a supported native checkpoint")
    return digest
