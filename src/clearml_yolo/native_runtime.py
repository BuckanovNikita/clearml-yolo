"""Scope native tracking settings to this invocation and inherited DDP workers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


@contextmanager
def native_runtime() -> Iterator[None]:
    """Disable only native ClearML callbacks without modifying the user's settings file."""
    previous = os.environ.get("YOLO_CONFIG_DIR")
    with TemporaryDirectory(prefix="cy-native-") as directory:
        os.environ["YOLO_CONFIG_DIR"] = directory
        try:
            from ultralytics.utils import SETTINGS, get_user_config_dir

            # This native helper has no upstream type annotations.
            settings_path = Path(get_user_config_dir()) / "settings.json"  # type: ignore[no-untyped-call]
            original = SETTINGS["clearml"]
            from ultralytics.utils.callbacks import clearml as integration

            callbacks: Any = integration.callbacks
            try:
                # Bypass SettingsManager persistence: change only process memory.
                dict.__setitem__(SETTINGS, "clearml", False)
                integration.callbacks = {}
                inherited = dict(SETTINGS)
                inherited.update(clearml=False, sync=False, api_key="", openai_api_key="")
                settings_path.write_text(json.dumps(inherited))
                yield
            finally:
                dict.__setitem__(SETTINGS, "clearml", original)
                integration.callbacks = callbacks
        finally:
            if previous is None:
                os.environ.pop("YOLO_CONFIG_DIR", None)
            else:
                os.environ["YOLO_CONFIG_DIR"] = previous
