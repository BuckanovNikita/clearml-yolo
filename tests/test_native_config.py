"""Native templates retain upstream documentation and stage semantics."""

from pathlib import Path

import pytest
import yaml


def test_stage_templates_preserve_all_upstream_comments() -> None:
    from clearml_yolo.native_config import native_template, render_native_yaml

    original = native_template()
    for stage in ("train", "predict"):
        rendered = render_native_yaml({"imgsz": 1280, "epochs": 2}, stage)
        for line in original.splitlines():
            if "#" in line:
                assert line[line.index("#") :] in rendered
        parsed = yaml.safe_load(rendered)
        assert parsed["imgsz"] == 1280
        assert ("epochs" in parsed) == (stage == "train")
        assert "format" not in parsed


def test_complete_upstream_mapping_is_filtered_for_prediction() -> None:
    from clearml_yolo.native_config import native_defaults, stage_settings

    settings = stage_settings(native_defaults(), "predict")
    assert settings["batch"] == 16
    assert "epochs" not in settings
    assert "lr0" not in settings
    assert "cfg" not in settings
    assert "conf" in settings


def test_unknown_and_raw_cfg_fail() -> None:
    from clearml_yolo.native_config import stage_settings

    with pytest.raises(ValueError, match="Unknown"):
        stage_settings({"not_a_native_parameter": 1}, "train")
    with pytest.raises(ValueError, match="cfg"):
        stage_settings({"cfg": "native.yaml"}, "train")


def test_export_has_no_hydra_wrapper_and_keeps_null(tmp_path: Path) -> None:
    from clearml_yolo.native_config import write_native_yaml

    path = write_native_yaml(tmp_path / "native.yaml", {"conf": None, "device": "cpu"}, "predict")
    values = yaml.safe_load(path.read_text())
    assert values["conf"] is None
    assert values["device"] == "cpu"
    assert "ultralytics" not in values


def test_prediction_only_rendering_options_are_commented_in_training() -> None:
    from clearml_yolo.native_config import native_defaults, render_native_yaml

    values = yaml.safe_load(render_native_yaml(native_defaults(), "train"))
    assert {"retina_masks", "save_crop", "show_boxes", "line_width"}.isdisjoint(values)
    assert {"show_conf", "show_labels"} <= values.keys()
