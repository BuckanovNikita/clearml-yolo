"""Check native parameter validation against the installed Ultralytics version."""

from __future__ import annotations

from pathlib import Path

import pytest
from omegaconf import OmegaConf
from ultralytics.cfg import get_cfg
from ultralytics.utils import DEFAULT_CFG_DICT

from clearml_yolo.configs import overlay_ultralytics_files


def test_both_input_styles_have_identical_effective_native_arguments(tmp_path: Path) -> None:
    raw = tmp_path / "native.yaml"
    raw.write_text("model: yolo11n.pt\nepochs: 3\namp: false\nbatch: 2\ndevice: cpu\n")
    source = OmegaConf.create({"cfg": str(raw), "ultralytics": {}})
    embedded = OmegaConf.create(
        {
            "cfg": None,
            "ultralytics": {
                "model": "yolo11n.pt",
                "epochs": 3,
                "amp": False,
                "batch": 2,
                "device": "cpu",
            },
        }
    )
    overlay_ultralytics_files("train")(source)
    overlay_ultralytics_files("train")(embedded)
    assert vars(get_cfg(overrides=dict(source.ultralytics))) == vars(
        get_cfg(overrides=dict(embedded.ultralytics))
    )


def test_native_invalid_parameter_is_rejected() -> None:
    with pytest.raises(SyntaxError):
        get_cfg(overrides={"nonexistent_release_option": True})


def test_explicit_native_defaults_survive_yaml(tmp_path: Path) -> None:
    raw = tmp_path / "native.yaml"
    raw.write_text("epochs: 3\n")
    config = OmegaConf.create(
        {"cfg": str(raw), "ultralytics": {"epochs": DEFAULT_CFG_DICT["epochs"]}}
    )
    overlay_ultralytics_files("train")(config)
    assert get_cfg(overrides=dict(config.ultralytics)).epochs == DEFAULT_CFG_DICT["epochs"]
