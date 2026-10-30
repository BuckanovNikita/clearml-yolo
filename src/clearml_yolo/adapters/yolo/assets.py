"""Describe native assets and explicitly configure persistent YOLO weight discovery."""

import importlib
import inspect
import json
from pathlib import Path

from filelock import FileLock

from clearml_yolo.core.assets import AssetSpec


class WeightCacheConfigurationError(RuntimeError):
    """The native weights directory could not be durably configured."""


def _read_settings(path: Path) -> dict[str, object]:
    # SDK settings are an opaque, versioned mapping. Preserve unknown fields too;
    # CY validates only the selector it owns rather than duplicating that schema.
    values: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, dict) or not isinstance(values.get("weights_dir"), str):
        raise TypeError("Ultralytics settings must contain a string weights_dir")
    return values


def _verify_settings(path: Path, expected: dict[str, object]) -> None:
    if _read_settings(path) != expected:
        raise ValueError("Ultralytics settings persistence did not match the update")


def configure_weights_directory() -> Path:
    """Persist an absolute native cache before preparation or worker startup.

    The adjacent lock coordinates CY callers. Other applications writing the same
    SDK settings must coordinate separately. Relative paths retain native literal
    semantics and are anchored to this invocation's working directory.
    """
    utilities = importlib.import_module("ultralytics.utils")
    settings = utilities.SETTINGS
    path = Path(settings.file_path).resolve()
    try:
        with FileLock(str(path.with_name(path.name + ".cy-weights.lock")), timeout=30):
            latest = _read_settings(path)
            directory = Path(str(latest["weights_dir"]))
            if not directory.is_absolute():
                directory = directory.resolve()
            expected = latest | {"weights_dir": str(directory)}
            if latest != expected:
                runtime = dict(settings)
                try:
                    # The supported update API persists the entire live mapping.
                    # Use latest disk values, then restore process-only switches
                    # (e.g. native callback ownership) without persisting them.
                    dict.clear(settings)
                    dict.update(settings, latest)
                    settings.update({"weights_dir": str(directory)})
                finally:
                    dict.clear(settings)
                    dict.update(settings, runtime)
            # The SDK may log and suppress a write error. Verify all disk values
            # before publishing the new location to consumers in this process.
            _verify_settings(path, expected)
            dict.update(settings, {"weights_dir": str(directory)})
            vars(utilities)["WEIGHTS_DIR"] = directory
            return directory
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise WeightCacheConfigurationError(
            f"Cannot persist Ultralytics weights_dir in {path} ({type(error).__name__}). "
            "Check the settings JSON and directory permissions, then rerun "
            "cy-download-weights from the original preparation directory."
        ) from error


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
