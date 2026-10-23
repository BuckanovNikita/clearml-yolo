"""Prepare verified native source at execution, including recovered detector checkpoints."""

import hashlib
import json
from pathlib import Path

from filelock import FileLock

from clearml_yolo.adapters.assets.archive import extract_source, source_manifest, validate_source
from clearml_yolo.adapters.assets.resolver import asset_destination, resolve_asset
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset


def source_directory(spec: AssetSpec) -> Path:
    return asset_destination(spec).with_suffix("").with_suffix("")


def existing_source(spec: AssetSpec) -> ResolvedAsset | None:
    destination = source_directory(spec)
    if not destination.exists():
        return None
    validate_source(destination)
    digest = hashlib.sha256(json.dumps(source_manifest(), sort_keys=True).encode()).hexdigest()
    return ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=destination,
        sha256=digest,
        content_kind="source-tree",
        override=spec.override,
        revision=spec.revision,
    )


def extract_resolved_source(record: ResolvedAsset) -> Path:
    if record.path.is_dir():
        return record.path
    destination = record.path.with_suffix("").with_suffix("")
    with FileLock(str(record.path) + ".lock", timeout=660):
        return extract_source(record.path, destination)


def prepare_deim_source() -> tuple[Path, ResolvedAsset]:
    """Resolve only DEIM source; inference never initializes pretrained backbones."""
    from clearml_yolo.adapters.deim.assets import source_asset

    spec = source_asset()
    record = existing_source(spec) or resolve_asset(spec)
    return extract_resolved_source(record), record
