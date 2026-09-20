"""Native integrations stay disabled in subprocesses without changing user settings."""

from __future__ import annotations

import json
import os
from pathlib import Path

from clearml_yolo.native_runtime import native_runtime


def test_child_settings_disable_clearml_and_restore_environment() -> None:
    previous = os.environ.get("YOLO_CONFIG_DIR")
    with native_runtime():
        directory = Path(os.environ["YOLO_CONFIG_DIR"])
        from ultralytics.utils import get_user_config_dir

        settings = json.loads((Path(get_user_config_dir()) / "settings.json").read_text())  # type: ignore[no-untyped-call]
        assert settings["clearml"] is False
        from ultralytics.utils import SETTINGS

        assert SETTINGS["clearml"] is False
    assert os.environ.get("YOLO_CONFIG_DIR") == previous
    assert not directory.exists()
