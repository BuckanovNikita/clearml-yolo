"""Native configuration contracts without loading model runtimes."""

import pytest

from clearml_yolo.native_config import native_defaults, stage_settings


def test_explicit_native_defaults_survive_projection() -> None:
    defaults = native_defaults()
    assert stage_settings(defaults, "train")["epochs"] == defaults["epochs"]


def test_native_invalid_parameter_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        stage_settings({"nonexistent_release_option": True}, "train")
