"""Use the installed approved RF-DETR asset registry without invoking its downloader."""

import importlib
from pathlib import Path

from clearml_yolo.adapters.rfdetr.backend import _VARIANTS, VERSION
from clearml_yolo.core.assets import AssetSpec


def pretrained_asset(preset: str) -> AssetSpec:
    registry = importlib.import_module("rfdetr.assets.model_weights")
    filename = _VARIANTS[preset][1]
    native = registry.ModelWeights.from_filename(filename)
    if native is None:
        raise ValueError(f"RF-DETR asset registry has no supported preset asset: {filename}")
    return AssetSpec(
        backend="rfdetr",
        preset=preset,
        filename=filename,
        canonical_url=str(native.url),
        checksum=str(native.md5_hash) if native.md5_hash else None,
        checksum_algorithm="md5",
        revision=VERSION,
        override="model.train.weights",
        cache_candidates=(Path(registry.get_model_cache_dir()) / filename, Path.cwd() / filename),
    )
