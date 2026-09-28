"""Native parser checks; kept separate from runtime-free configuration tests."""

from pathlib import Path

import pytest

from clearml_yolo.native_config import Stage, native_defaults, write_native_yaml


@pytest.mark.parametrize("stage", ["train", "predict"])
def test_export_loads_directly_in_native_parser(tmp_path: Path, stage: Stage) -> None:
    from ultralytics.cfg import get_cfg

    settings = native_defaults() | {"model": "yolo11n.pt", "device": "cpu", "mode": stage}
    path = write_native_yaml(tmp_path / "native.yaml", settings, stage)
    config = get_cfg(cfg=str(path))
    assert config.model == "yolo11n.pt"
    assert config.device == "cpu"
    assert config.mode == stage


def test_native_invalid_parameter_is_rejected() -> None:
    from ultralytics.cfg import get_cfg

    with pytest.raises(SyntaxError):
        get_cfg(overrides={"nonexistent_release_option": True})
