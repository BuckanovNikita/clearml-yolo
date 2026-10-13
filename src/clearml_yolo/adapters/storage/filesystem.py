"""Contained project writes with unchanged external input and library paths."""

import os
from pathlib import Path

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
    invocation_temporary_root,
    project_write_path,
)


def write_path(value: str | Path) -> Path:
    """Validate containment before a project-owned write or directory creation."""
    return project_write_path(value)


def validate_output_tree(value: str | Path) -> Path:
    """Preflight existing native outputs, including contained directory aliases.

    Native trainers choose dynamic checkpoint/plot names. Check their selected
    output subtree before handing them control without changing SDK cache policy.
    This is a preflight for cooperating callers, not protection from concurrent
    replacement of filesystem entries after validation.
    """
    root = write_path(value)
    pending = [root]
    visited: set[Path] = set()
    while pending:
        path = write_path(pending.pop())
        resolved = path.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)
        if path.is_dir():
            pending.extend(path.iterdir())
    return root


def cy_home() -> Path:
    """Resolve the workspace; CLI startup freezes relative values before any chdir."""
    return Path(os.environ.get("CY_HOME") or Path.cwd()).expanduser().resolve()


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
