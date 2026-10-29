"""Describe Ultralytics assets using its effective settings and native release."""

import importlib
import inspect
from pathlib import Path

from clearml_yolo.core.assets import AssetSpec


def pretrained_asset(filename: str) -> AssetSpec:
    downloads = importlib.import_module("ultralytics.utils.downloads")
    checks = importlib.import_module("ultralytics.utils.checks")
    utilities = importlib.import_module("ultralytics.utils")
    name = str(checks.check_yolov5u_filename(filename, verbose=False))
    if name not in downloads.GITHUB_ASSETS_NAMES:
        raise ValueError(f"Unknown native Ultralytics detection asset: {name}")
    # The installed loader owns release selection. Introspection reads its public
    # call defaults without triggering downloads or hard-coding a second version.
    defaults = inspect.signature(downloads.attempt_download_asset).parameters
    release = str(defaults["release"].default)
    repository = str(defaults["repo"].default)
    root = Path(utilities.SETTINGS["weights_dir"]).resolve()
    return AssetSpec(
        backend="ultralytics",
        preset=Path(name).stem,
        filename=name,
        canonical_url=f"https://github.com/{repository}/releases/download/{release}/{name}",
        revision=release,
        override="ultralytics.model",
        native_cache=root,
        cache_candidates=(Path.cwd() / name,),
    )
