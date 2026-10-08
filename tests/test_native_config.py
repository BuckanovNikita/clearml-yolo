"""Native templates retain upstream documentation and stage semantics."""

from pathlib import Path
from typing import Literal

import pytest
import yaml


def test_stage_templates_preserve_all_upstream_comments() -> None:
    from clearml_yolo.adapters.yolo.config import native_template, render_native_yaml

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
    from clearml_yolo.adapters.yolo.config import native_defaults, stage_settings

    settings = stage_settings(native_defaults(), "predict")
    assert settings["batch"] == 16
    assert "epochs" not in settings
    assert "lr0" not in settings
    assert "cfg" not in settings
    assert "conf" in settings


def test_unknown_and_raw_cfg_fail() -> None:
    from clearml_yolo.adapters.yolo.config import stage_settings

    with pytest.raises(ValueError, match="Unknown"):
        stage_settings({"not_a_native_parameter": 1}, "train")
    with pytest.raises(ValueError, match="cfg"):
        stage_settings({"cfg": "native.yaml"}, "train")


def test_export_has_no_hydra_wrapper_and_keeps_null(tmp_path: Path) -> None:
    from clearml_yolo.adapters.yolo.config import write_native_yaml

    path = write_native_yaml(tmp_path / "native.yaml", {"conf": None, "device": "cpu"}, "predict")
    values = yaml.safe_load(path.read_text())
    assert values["conf"] is None
    assert values["device"] == "cpu"
    assert "ultralytics" not in values


def test_prediction_only_rendering_options_are_commented_in_training() -> None:
    from clearml_yolo.adapters.yolo.config import native_defaults, render_native_yaml

    values = yaml.safe_load(render_native_yaml(native_defaults(), "train"))
    assert {"retina_masks", "save_crop", "show_boxes", "line_width"}.isdisjoint(values)
    assert {"show_conf", "show_labels"} <= values.keys()


def test_project_defaults_are_explicit() -> None:
    from clearml_yolo.adapters.yolo.config import native_defaults

    defaults = native_defaults()
    assert {key: defaults[key] for key in ("imgsz", "compile", "nms", "model")} == {
        "imgsz": 960,
        "compile": True,
        "nms": True,
        "model": "yolo11n.pt",
    }


@pytest.mark.parametrize("stage", ["train", "predict"])
def test_irrelevant_detection_parameters_are_commented(stage: Literal["train", "predict"]) -> None:
    from clearml_yolo.adapters.yolo.config import native_defaults, render_native_yaml

    rendered = render_native_yaml(native_defaults(), stage)
    values = yaml.safe_load(rendered)
    irrelevant = {
        "overlap_mask",
        "mask_ratio",
        "dropout",
        "pose",
        "kobj",
        "rle",
        "angle",
        "dlog",
        "dgrad",
        "dlam",
        "copy_paste",
        "copy_paste_mode",
        "auto_augment",
        "erasing",
        "retina_masks",
        "vid_stride",
        "stream_buffer",
        "save_frames",
        "embed",
    }
    assert irrelevant.isdisjoint(values)
    assert values["nms"] is True
    for key in irrelevant:
        assert f"# {key}:" in rendered


def test_partial_render_does_not_invent_unobserved_values() -> None:
    from clearml_yolo.adapters.yolo.config import render_native_yaml

    assert yaml.safe_load(render_native_yaml({"imgsz": 906}, "predict")) == {"imgsz": 906}


@pytest.mark.parametrize("alias", ["end2end", "half", "int8", "keras"])
def test_unrecognized_native_keys_fail_strict_validation(alias: str) -> None:
    from clearml_yolo.adapters.yolo.config import stage_settings

    with pytest.raises(ValueError, match=r"Unknown Ultralytics parameters"):
        stage_settings({alias: True}, "predict")


def test_prediction_settings_reject_sparse_or_missing_section() -> None:
    from clearml_yolo.adapters.yolo.config import prediction_settings

    for overrides in ({}, {"conf": 0.1}):
        with pytest.raises(ValueError, match=r"complete|Missing"):
            prediction_settings(overrides, "weights.pt")


def test_execution_validates_stage_and_image_size() -> None:
    from clearml_yolo.adapters.yolo import config as native_config

    assert hasattr(native_config, "execution_settings")
    defaults = native_config.native_defaults()
    for key, value, match in [
        ("task", "segment", "detect"),
        ("mode", "predict", "mode"),
        ("imgsz", None, "imgsz"),
        ("imgsz", True, "imgsz"),
        ("imgsz", 0, "imgsz"),
        ("embed", [1], "embed"),
    ]:
        with pytest.raises(ValueError, match=match):
            native_config.execution_settings(defaults | {key: value}, "train")
    values = native_config.execution_settings(defaults | {"compile": False, "conf": None}, "train")
    assert values["compile"] is False
    assert values["conf"] is None


def test_native_training_list_size_is_not_wrapper_normalized() -> None:
    from clearml_yolo.adapters.yolo.config import execution_settings, native_defaults

    values = execution_settings(native_defaults() | {"imgsz": [906, 640]}, "train")
    assert values["imgsz"] == [906, 640]


def test_classification_covers_template_once_and_preserves_detection_losses() -> None:
    from clearml_yolo.adapters.yolo.config import (
        INACTIVE_KEYS,
        PREDICT_KEYS,
        TRAIN_KEYS,
        native_defaults,
        stage_settings,
    )

    assert native_defaults().keys() <= TRAIN_KEYS | PREDICT_KEYS | INACTIVE_KEYS
    assert INACTIVE_KEYS.isdisjoint(TRAIN_KEYS | PREDICT_KEYS)
    train = stage_settings(native_defaults(), "train")
    assert train["epochs"] == native_defaults()["epochs"]
    assert {"box", "cls", "cls_pw", "dfl", "distill_model", "dis", "cutmix"} <= train.keys()
    assert "dnn" not in train
