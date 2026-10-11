"""Workspace defaults without restricting explicitly selected destinations."""

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

from clearml_yolo.adapters.observability.diagnostics import log_exception, redact_text
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
    invocation_temporary_root,
)

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
    directory = write_path(invocation_temporary_root() or cy_home() / ".tmp")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _fiftyone_inputs() -> dict[str, object]:
    # Never probe the home fallback, including for explicit embedding callers.
    source = (
        Path(os.environ.get("FIFTYONE_CONFIG_PATH") or cy_home() / ".config/fiftyone/config.json")
        .expanduser()
        .resolve()
    )
    if not source.is_relative_to(cy_home()):
        raise ValueError(
            f"FIFTYONE_CONFIG_PATH must resolve inside the physical project root: {source}"
        )
    try:
        if not source.is_file():
            return {}
        values = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            logger.warning(
                "Optional FiftyOne configuration must be a mapping; using defaults: {}",
                redact_text(str(source)),
            )
            return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        log_exception(
            "Cannot read optional FiftyOne configuration; using defaults",
            error,
            context={"source": source},
        )
        return {}
    return {str(key): value for key, value in values.items()}


@trace_operation("storage.filesystem.initialize")
def initialize_filesystem() -> None:
    """Delegate the pre-import policy; invocation scratch is explicitly scoped."""
    initialize_runtime_environment()
    _fiftyone_inputs()  # Retain diagnostics for invalid optional project settings.
