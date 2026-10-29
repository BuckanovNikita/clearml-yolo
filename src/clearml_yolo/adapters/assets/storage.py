"""Explicit SDK asset storage, separate from contained application output writes."""

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path


def native_asset_path(root: Path, filename: str) -> Path:
    """Allow a native cache root while rejecting escaping asset/lock symlinks."""
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("Native asset filename must be a single component")
    directory = root.expanduser().resolve()
    destination = directory / filename
    if not destination.resolve().is_relative_to(directory):
        raise ValueError("Asset destination escapes its configured native cache")
    return destination


def promote_asset(
    source: Path, destination: Path, *, validator: Callable[[Path], str] | None = None
) -> None:
    """Copy validated legacy bytes atomically without consuming the original file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=".asset-", dir=destination.parent, delete=False
    ) as temporary:
        staging = Path(temporary.name)
    try:
        with source.open("rb") as incoming, staging.open("wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        if validator is not None:
            validator(staging)
        staging.replace(destination)
    finally:
        staging.unlink(missing_ok=True)
