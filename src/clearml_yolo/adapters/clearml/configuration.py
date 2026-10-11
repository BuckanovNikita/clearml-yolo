"""Configure SDK state paths that have no environment selectors."""

import os
from pathlib import Path

from clearml_yolo.adapters.storage.filesystem import cy_home


def configure_sdk_state() -> None:
    """Select project state before Task.init and retain it through SDK shutdown."""
    from botocore.loaders import Loader  # type: ignore[import-untyped]
    from clearml.config.cache import SessionCache

    # The installed SDK exposes this mutable constant without a typed configuration
    # API. Fail closed if that interface changes instead of using its home fallback.
    if not isinstance(SessionCache.SESSION_CACHE_FOLDER, str):
        raise TypeError("Unsupported ClearML session cache configuration interface")
    # Botocore searches this user model override directory before packaged models.
    # AWS_DATA_PATH adds more directories but cannot disable its home fallback.
    if not isinstance(Loader.CUSTOMER_DATA_PATH, str):
        raise TypeError("Unsupported botocore model configuration interface")
    root = cy_home()
    directory = _state_path(
        root, Path(os.environ.get("XDG_CACHE_HOME", root / ".cache")) / "clearml/session"
    )
    model_directory = _state_path(
        root, Path(os.environ.get("XDG_CONFIG_HOME", root / ".config")) / "aws/models"
    )
    directory.mkdir(parents=True, exist_ok=True)
    model_directory.mkdir(parents=True, exist_ok=True)
    SessionCache.SESSION_CACHE_FOLDER = str(directory)
    Loader.CUSTOMER_DATA_PATH = str(model_directory)


def _state_path(root: Path, selected: Path) -> Path:
    selected = selected.expanduser()
    selected = (selected if selected.is_absolute() else root / selected).resolve()
    if not selected.is_relative_to(root):
        raise ValueError(f"SDK state must resolve inside the physical project root: {selected}")
    return selected
