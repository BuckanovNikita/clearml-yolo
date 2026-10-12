"""Project workspace paths preserve library defaults and explicit destinations."""

import os
from pathlib import Path

from loguru import logger

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
    invocation_temporary_root,
)

_WARNED_HOME_PATHS: set[Path] = set()


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


def model_weights_path(value: str | Path) -> str | Path:
    """Recognize existing local files, leaving library model lookup unchanged."""
    if isinstance(value, str) and "://" not in value:
        candidate = Path(value).expanduser()
        if candidate.is_file():
            return candidate
    return value


def temporary_root() -> Path:
    """Provide an explicit project directory without changing global temp settings."""
    active = invocation_temporary_root()
    if active is not None:
        directory = write_path(active)
    else:
        root = cy_home()
        selected = Path(os.environ.get("CY_RUNTIME_TEMP_ROOT") or root / ".tmp").expanduser()
        directory = write_path(selected if selected.is_absolute() else root / selected).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@trace_operation("storage.filesystem.initialize")
def initialize_filesystem() -> None:
    """Initialize project workspace paths without reading library configuration."""
    initialize_runtime_environment()
