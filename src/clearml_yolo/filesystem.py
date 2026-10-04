"""Workspace defaults without restricting explicitly selected destinations."""

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

_WARNED_HOME_PATHS: set[Path] = set()
_NATIVE_WEIGHTS: ContextVar[Path | None] = ContextVar("cy_native_weights", default=None)


def write_path(value: str | Path) -> Path:
    """Preserve an explicit path, warning once about its physical home destination."""
    path = Path(value).expanduser()
    resolved = path.resolve()
    if resolved.is_relative_to(Path.home().resolve()) and resolved not in _WARNED_HOME_PATHS:
        logger.warning("Write destination is physically inside user home: {}", resolved)
        _WARNED_HOME_PATHS.add(resolved)
    return path


def cy_home() -> Path:
    """Resolve the workspace; CLI startup freezes relative values before any chdir."""
    return write_path(os.environ.get("CY_HOME") or Path.cwd()).resolve()


def runs_root() -> Path:
    return write_path(cy_home() / "runs")


@contextmanager
def native_weights_directory(directory: Path) -> Iterator[None]:
    token = _NATIVE_WEIGHTS.set(directory)
    try:
        yield
    finally:
        _NATIVE_WEIGHTS.reset(token)


def model_weights_path(value: str | Path) -> str | Path:
    """Keep existing/explicit inputs; download absent bare checkpoints into the workspace."""
    if isinstance(value, str) and "://" in value:
        return value
    candidate = Path(value).expanduser()
    if candidate.exists() or candidate.suffix != ".pt":
        return candidate
    if isinstance(value, str) and value == candidate.name:
        root = _NATIVE_WEIGHTS.get() or cy_home() / ".cache" / "ultralytics" / "weights"
        candidate = root / candidate.name
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return write_path(candidate)


def temporary_root() -> Path:
    """Project-owned temporary files never depend on the system temporary directory."""
    directory = write_path(cy_home() / ".tmp")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _fiftyone_inputs() -> dict[str, object]:
    # Read explicit data selections without changing the dependency's configuration paths.
    source = Path(os.environ.get("FIFTYONE_CONFIG_PATH") or
                  Path.home() / ".fiftyone" / "config.json").expanduser()
    try:
        if not source.is_file():
            return {}
        values = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            logger.warning("Optional FiftyOne configuration must be a mapping; using defaults")
            return {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        logger.warning("Cannot read optional FiftyOne configuration; using defaults")
        return {}
    return {str(key): value for key, value in values.items()}


def initialize_filesystem() -> None:
    """Set project data defaults before import, preserving explicit environment settings.

    Settings stay in the process environment so spawned native workers inherit them.
    No home variable is changed and no existing user configuration is rewritten.
    """
    root = cy_home()
    os.environ["CY_HOME"] = str(root)
    cache = root / ".cache"
    config = root / ".config"
    fiftyone_inputs = _fiftyone_inputs()
    defaults = {
        "YOLO_CONFIG_DIR": config,
        "CLEARML_CACHE_DIR": cache / "clearml",
        "FIFTYONE_DATABASE_DIR": cache / "fiftyone" / "database",
        "FIFTYONE_DEFAULT_DATASET_DIR": cache / "fiftyone" / "datasets",
        "FIFTYONE_DATASET_ZOO_DIR": cache / "fiftyone" / "datasets",
    }
    for name, default in defaults.items():
        selected = None
        if name.startswith("FIFTYONE_"):
            configured = fiftyone_inputs.get(name.removeprefix("FIFTYONE_").lower())
            if isinstance(configured, str) and configured:
                selected = configured
        destination = write_path(os.environ.setdefault(name, str(selected or default)))
        destination.mkdir(parents=True, exist_ok=True)
