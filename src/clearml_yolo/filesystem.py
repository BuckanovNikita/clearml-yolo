"""Workspace defaults without restricting explicitly selected destinations."""

import json
import os
import tempfile
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


def _fiftyone_inputs(config: Path) -> dict[str, object]:
    for kind in ("", "APP_", "ANNOTATION_", "EVALUATION_"):
        name = f"FIFTYONE_{kind}CONFIG_PATH"
        filename = f"{kind.lower()}config.json"
        existing = Path.home() / ".fiftyone" / filename
        default = existing if existing.is_file() else config / "fiftyone" / filename
        # Existing credentials/configuration stay read-only, never copied or rewritten.
        os.environ.setdefault(name, str(default))
    source = Path(os.environ["FIFTYONE_CONFIG_PATH"]).expanduser()
    if not source.is_file():
        return {}
    try:
        values = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise ValueError("FiftyOne configuration is not valid JSON") from None
    if not isinstance(values, dict):
        raise TypeError("FiftyOne configuration must be a mapping")
    return {str(key): value for key, value in values.items()}


def initialize_filesystem() -> None:
    """Set dependency defaults before import, preserving explicit environment settings.

    Settings stay in the process environment so spawned native workers inherit them.
    No home variable is changed and no existing user configuration is rewritten.
    """
    root = cy_home()
    os.environ["CY_HOME"] = str(root)
    cache = root / ".cache"
    config = root / ".config"
    fiftyone_inputs = _fiftyone_inputs(config)
    defaults = {
        "XDG_CACHE_HOME": cache,
        "XDG_CONFIG_HOME": config,
        "YOLO_CONFIG_DIR": config,
        "CLEARML_CACHE_DIR": cache / "clearml",
        "MPLCONFIGDIR": config / "matplotlib",
        "TORCH_HOME": cache / "torch",
        "TORCH_EXTENSIONS_DIR": cache / "torch-extensions",
        "TORCHINDUCTOR_CACHE_DIR": cache / "torchinductor",
        "TRITON_CACHE_DIR": cache / "triton",
        "CUDA_CACHE_PATH": cache / "cuda",
        "NUMBA_CACHE_DIR": cache / "numba",
        "HF_HOME": cache / "huggingface",
        "PYTHONPYCACHEPREFIX": cache / "python",
        "FIFTYONE_DATABASE_DIR": cache / "fiftyone" / "database",
        "FIFTYONE_DEFAULT_DATASET_DIR": cache / "fiftyone" / "datasets",
        "FIFTYONE_DATASET_ZOO_DIR": cache / "fiftyone" / "datasets",
        "FIFTYONE_MODEL_ZOO_DIR": cache / "fiftyone" / "models",
        "FIFTYONE_PLUGINS_DIR": config / "fiftyone" / "plugins",
        "ETA_CONFIG_DIR": config / "eta",
        "ETA_OUTPUT_DIR": cache / "eta",
    }
    for name, default in defaults.items():
        # The legacy ClearML alias is also an explicit user selection.
        selected = os.environ.get("TRAINS_CACHE_DIR") if name == "CLEARML_CACHE_DIR" else None
        if name.startswith("FIFTYONE_"):
            configured = fiftyone_inputs.get(name.removeprefix("FIFTYONE_").lower())
            if isinstance(configured, str) and configured:
                selected = configured
        destination = write_path(os.environ.setdefault(name, str(selected or default)))
        destination.mkdir(parents=True, exist_ok=True)
    selected_temp = os.environ.get("TMP") or os.environ.get("TEMP") or str(root / ".tmp")
    destination = write_path(os.environ.setdefault("TMPDIR", selected_temp))
    destination.mkdir(parents=True, exist_ok=True)
    # tempfile may already have cached a system directory before CLI startup.
    tempfile.tempdir = str(destination.resolve())
