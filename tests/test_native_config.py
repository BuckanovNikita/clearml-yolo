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
    assert {key: defaults[key] for key in ("imgsz", "compile", "nms", "model", "iou")} == {
        "imgsz": 960,
        "compile": True,
        "nms": True,
        "model": "yolo11n.pt",
        "iou": 0.7,
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


# Ultralytics 8.4.218 ships image tiling keys and a null NMS IoU, which
# upstream resolves per stage (predict/export 0.5, val 0.7). Both upstream layouts are
# derived from the installed template so the checks hold on either installed version.
_OLD_IOU = "iou: 0.7 # (float) IoU threshold used for NMS"
_NEW_IOU = "iou: # (float, optional) NMS IoU threshold; defaults: predict/export=0.5, val=0.7"
_TILE_LINES = (
    "tile: False # (bool | int | list) enable tiling; True uses imgsz, int or [h, w] sets tile size in source pixels",
    "tile_overlap: 0.2 # (float) fraction of each tile shared with its neighbor (0.0-<1.0)",
)
_Layout = Literal["old", "new"]


def _upstream_template(layout: _Layout) -> str:
    from clearml_yolo.adapters.yolo.config import native_template

    lines: list[str] = []
    for line in native_template().splitlines():
        if line.startswith(("tile:", "tile_overlap:")):
            continue
        if line.startswith("iou:"):
            line = _OLD_IOU if layout == "old" else _NEW_IOU  # noqa: PLW2901 - substitute the upstream entry
        lines.append(line)
        if layout == "new" and line.startswith("nms:"):
            lines.extend(_TILE_LINES)
    return "\n".join(lines) + "\n"


def _install_template(monkeypatch: pytest.MonkeyPatch, layout: _Layout) -> None:
    from clearml_yolo.adapters.yolo import config as native_config

    template = _upstream_template(layout)
    monkeypatch.setattr(native_config, "native_template", lambda: template)


def _saved_groups(monkeypatch: pytest.MonkeyPatch, layout: _Layout) -> tuple[dict[str, object], dict[str, object]]:
    """Complete training and resolved prediction groups as composed under ``layout``."""
    from omegaconf import OmegaConf

    from clearml_yolo.adapters.yolo.config import native_defaults, prediction_defaults, stage_settings

    _install_template(monkeypatch, layout)
    train = stage_settings(native_defaults(), "train")
    config = OmegaConf.create({"ultralytics": train, "ultralytics_predict": prediction_defaults()})
    predict = OmegaConf.to_container(config.ultralytics_predict, resolve=True)
    assert isinstance(predict, dict)
    return train, {str(key): value for key, value in predict.items()}


@pytest.mark.parametrize("layout", ["old", "new"])
def test_upstream_tiling_keys_are_inactive_and_nms_iou_is_pinned(
    monkeypatch: pytest.MonkeyPatch, layout: _Layout
) -> None:
    from clearml_yolo.adapters.yolo.config import INACTIVE_KEYS, native_defaults, prediction_defaults, stage_settings

    _install_template(monkeypatch, layout)
    defaults = native_defaults()
    assert defaults["iou"] == 0.7
    assert {"tile", "tile_overlap"} <= INACTIVE_KEYS
    for stage in ("train", "predict"):
        settings = stage_settings(defaults, stage)
        assert settings["iou"] == 0.7
        assert {"tile", "tile_overlap"}.isdisjoint(settings)
    assert prediction_defaults()["iou"] == "${ultralytics.iou}"
    assert prediction_defaults(inherit=False)["iou"] == 0.7
    assert {"tile", "tile_overlap"}.isdisjoint(prediction_defaults())


@pytest.mark.parametrize(("saved", "installed"), [("old", "new"), ("new", "old")])
def test_complete_groups_execute_across_upstream_template_change(
    monkeypatch: pytest.MonkeyPatch, saved: _Layout, installed: _Layout
) -> None:
    from clearml_yolo.adapters.yolo.config import execution_settings, prediction_settings

    train, predict = _saved_groups(monkeypatch, saved)
    _install_template(monkeypatch, installed)
    assert execution_settings(train, "train")["iou"] == 0.7
    assert execution_settings(predict, "predict")["iou"] == 0.7
    assert prediction_settings(predict, "weights.pt")["iou"] == 0.7


@pytest.mark.parametrize("layout", ["old", "new"])
def test_null_nms_iou_stays_rejected(monkeypatch: pytest.MonkeyPatch, layout: _Layout) -> None:
    from clearml_yolo.adapters.yolo.config import execution_settings

    train, predict = _saved_groups(monkeypatch, layout)
    with pytest.raises(ValueError, match=r"^ultralytics\.iou must not be null$"):
        execution_settings(train | {"iou": None}, "train")
    with pytest.raises(ValueError, match=r"^ultralytics_predict\.iou must not be null$"):
        execution_settings(predict | {"iou": None}, "predict")


def test_generated_examples_pin_nms_iou_under_tiling_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    from clearml_yolo.adapters.yolo.config import native_defaults, render_native_yaml
    from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree

    _install_template(monkeypatch, "new")
    dump_config_tree(tmp_path)
    training_text = (tmp_path / "ultralytics/default.yaml").read_text()
    training = yaml.safe_load(training_text)
    prediction = yaml.safe_load((tmp_path / "ultralytics_predict/default.yaml").read_text())
    assert training["iou"] == 0.7
    assert prediction["iou"] == "${ultralytics.iou}"
    assert {"tile", "tile_overlap"}.isdisjoint(training.keys() | prediction.keys())
    assert "# tile: False #" in training_text
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="cy")
    resolved = OmegaConf.to_container(config.ultralytics_predict, resolve=True)
    assert isinstance(resolved, dict)
    assert resolved["iou"] == 0.7
    for stage in ("train", "predict"):
        assert yaml.safe_load(render_native_yaml(native_defaults(), stage))["iou"] == 0.7


@pytest.mark.parametrize(("saved", "installed"), [("old", "new"), ("new", "old")])
def test_detector_preflight_accepts_unchanged_yolo_groups_across_template_change(
    monkeypatch: pytest.MonkeyPatch, saved: _Layout, installed: _Layout
) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store
    from omegaconf import OmegaConf

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - registers the Hydra configurations
    from clearml_yolo.adapters.yolo.config import prediction_defaults
    from clearml_yolo.application.use_cases.train import train
    from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train", overrides=["model=deimv2/s", "ground_truth=truth.csv"])
    training, _ = _saved_groups(monkeypatch, saved)
    config.ultralytics = OmegaConf.create(training)
    config.ultralytics_predict = OmegaConf.create(prediction_defaults())
    _install_template(monkeypatch, installed)
    validate_wrapper_keys(config, train)


def test_real_native_prediction_records_renderable_arguments_with_the_pinned_nms_iou(tmp_path: Path) -> None:
    import cv2
    import numpy as np

    from clearml_yolo.adapters.yolo.config import render_native_yaml
    from clearml_yolo.adapters.yolo.inference import predict_on_images
    from native_config_helpers import prediction_config

    # Unmocked: an untrained model built from the packaged architecture, scored on CPU.
    image = tmp_path / "image.png"
    assert cv2.imwrite(str(image), np.zeros((64, 64, 3), dtype=np.uint8))
    settings = prediction_config(
        device="cpu", compile=False, imgsz=64, batch=1, project=str(tmp_path / "native"), name="predict"
    )
    for key in ("model", "source"):
        settings.pop(key)
    frame = predict_on_images("yolo11n.yaml", [str(image)], **settings)
    effective = frame.attrs["effective_args"]
    assert effective["iou"] == 0.7
    rendered = yaml.safe_load(render_native_yaml(effective, "predict"))
    assert rendered["iou"] == 0.7
    assert rendered["mode"] == "predict"
