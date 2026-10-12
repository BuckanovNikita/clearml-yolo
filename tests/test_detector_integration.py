"""Native detector outputs retain the shared prediction and checkpoint contracts."""

from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pandas as pd
import pytest

from clearml_yolo.adapters.integrations.detectors import DetectorRunner
from clearml_yolo.adapters.storage.checkpoint import bind_checkpoint
from clearml_yolo.application.contracts import ModelRef
from clearml_yolo.core.models import CheckpointMetadata, Preprocessing, model_preset
from clearml_yolo.entrypoints.composition import build_dependencies


def test_prediction_settings_use_selected_recipe_and_explicit_weights() -> None:
    runner = DetectorRunner(model_preset("rfdetr/small"), build_dependencies().model)
    settings = runner.prediction_settings({"device": "cpu", "batch": 2}, "best.pth")
    assert settings["model"] == "best.pth"
    assert (
        settings["imgsz"] is None
    )  # Resolve the recorded training size after downloading weights.
    assert settings["batch"] == 2
    assert settings["device"] == "cpu"


def test_checkpoint_selects_backend_and_restores_image_join_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.rfdetr import backend

    weights = tmp_path / "best.pth"
    with ZipFile(weights, "w") as archive:
        archive.writestr("best/data.pkl", b"test")
    bind_checkpoint(
        weights,
        CheckpointMetadata(
            backend="rfdetr",
            preset="small",
            class_names=("0001",),
            preprocessing=Preprocessing(resize="stretch", size=512),
        ),
    )
    source = str(tmp_path / "0002.png")

    def native_predict(*args: Any) -> pd.DataFrame:
        assert args[1].class_names == ("0001",)
        assert args[3] == [source]
        frame = pd.DataFrame(
            [[source, "0001", 0.9, 1.0, 2.0, 10.0, 20.0]],
            columns=[
                "image_name",
                "instance_label",
                "confidence",
                "bbox_x_tl",
                "bbox_y_tl",
                "bbox_x_br",
                "bbox_y_br",
            ],
        )
        frame.attrs["image_paths"] = [source]
        return frame

    monkeypatch.setattr(backend, "predict", native_predict)
    runner = DetectorRunner(model_preset("ultralytics"), build_dependencies().model)
    frame = runner.predict_on_images(
        weights,
        [source],
        image_name="stem",
        manifest_dir=tmp_path / "inputs",
        device="cpu",
        imgsz=512,
        project=str(tmp_path),
        name="predict",
    )
    assert frame.image_name.tolist() == ["0002"]
    assert frame.instance_label.tolist() == ["0001"]
    assert frame.attrs["checkpoint_design"]["backend"] == "rfdetr"
    assert Path(frame.attrs["effective_args"]["source"]).read_text().splitlines() == [source]


def test_raw_reference_requires_checkpoint_owned_labels(tmp_path: Path) -> None:
    weights = tmp_path / "raw.pth"
    weights.write_bytes(b"external")
    runner = build_dependencies().model
    reference = ModelRef(
        source="local", weights=weights, thresholds={"0001": 0.4}, backend="rfdetr", preset="small"
    )
    with pytest.raises(ValueError, match=r"class_names.*preprocessing"):
        runner.bind_reference(weights, reference)
    reference = reference.model_copy(
        update={
            "class_names": ("0001",),
            "preprocessing": Preprocessing(resize="stretch", size=512),
        }
    )
    runner.bind_reference(weights, reference)
    assert runner.trained_imgsz(weights) == 512
    assert weights.read_bytes() == b"external"


def test_reference_rejects_conflicting_embedded_descriptor(tmp_path: Path) -> None:
    weights = tmp_path / "best.pth"
    with ZipFile(weights, "w") as archive:
        archive.writestr("best/data.pkl", b"test")
    bind_checkpoint(
        weights,
        CheckpointMetadata(
            backend="rfdetr",
            preset="small",
            class_names=("0001",),
            preprocessing=Preprocessing(resize="stretch", size=512),
        ),
    )
    reference = ModelRef(
        source="local",
        weights=weights,
        thresholds={"0001": 0.4},
        backend="fasterrcnn",
        preset="resnet50_fpn",
    )
    with pytest.raises(ValueError, match="disagrees"):
        build_dependencies().model.bind_reference(weights, reference)


@pytest.mark.parametrize(
    "conflict",
    [
        {"class_names": ("different",)},
        {"preprocessing": Preprocessing(resize="stretch", size=640)},
        {"preset": "medium"},
        {"backend": None, "preset": None, "class_names": None, "preprocessing": None},
    ],
)
def test_same_raw_checkpoint_rejects_conflicting_comparison_metadata(
    tmp_path: Path, conflict: dict[str, Any]
) -> None:
    weights = tmp_path / "raw.pth"
    weights.write_bytes(b"external")
    runner = build_dependencies().model
    reference = ModelRef(
        source="local",
        weights=weights,
        thresholds={"0001": 0.4},
        backend="rfdetr",
        preset="small",
        class_names=("0001",),
        preprocessing=Preprocessing(resize="stretch", size=512),
    )
    runner.bind_reference(weights, reference)
    changed = ModelRef.model_validate(reference.model_dump() | conflict)
    with pytest.raises(ValueError, match=r"Conflicting.*same checkpoint"):
        runner.bind_reference(weights, changed)
    assert runner.trained_imgsz(weights) == 512
    assert weights.read_bytes() == b"external"


def test_same_raw_checkpoint_accepts_distinct_thresholds_and_display_labels(tmp_path: Path) -> None:
    weights = tmp_path / "raw.pth"
    weights.write_bytes(b"external")
    runner = build_dependencies().model
    reference = ModelRef(
        source="local",
        weights=weights,
        thresholds={"0001": 0.4},
        label="candidate",
        backend="rfdetr",
        preset="small",
        class_names=("0001",),
        preprocessing=Preprocessing(resize="stretch", size=512),
    )
    runner.bind_reference(weights, reference)
    runner.bind_reference(
        weights, reference.model_copy(update={"thresholds": {"0001": 0.7}, "label": "baseline"})
    )
    assert runner.trained_imgsz(weights) == 512


def test_new_family_comparison_passes_shared_precision_to_yolo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.entrypoints.composition import _ModelRunner

    received: dict[str, Any] = {}

    def legacy_predict(*args: Any, **kwargs: Any) -> pd.DataFrame:
        received.update(kwargs)
        return pd.DataFrame()

    monkeypatch.setattr(_ModelRunner, "predict_on_images", staticmethod(legacy_predict))
    runner = DetectorRunner(model_preset("rfdetr/small"), _ModelRunner())
    runner.bind_reference(
        tmp_path / "old.pt",
        ModelRef(source="local", weights=tmp_path / "old.pt", thresholds={"cat": 0.5}),
    )
    runner.predict_on_images(tmp_path / "old.pt", [], half=True, backend="rfdetr", preset="small")
    assert received["quantize"] == 16
    assert {"half", "backend", "preset"}.isdisjoint(received)


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("classes", [0]),
        ("single_cls", True),
        ("fraction", 0.5),
        ("cls_remap", {0: 1}),
        ("data", "another-dataset.yaml"),
        ("split", "test"),
    ],
)
def test_native_comparison_rejects_unsupported_population_controls(
    setting: str, value: Any
) -> None:
    with pytest.raises(ValueError, match=f"Unsupported.*{setting}"):
        DetectorRunner._native_prediction({setting: value})


def test_native_comparison_accepts_unchanged_yolo_population_defaults() -> None:
    settings = DetectorRunner._native_prediction(
        {"classes": None, "single_cls": False, "fraction": 1.0, "cls_remap": True, "data": None}
    )
    assert settings.conf == 0.001


@pytest.mark.parametrize(
    ("settings", "match"),
    [
        ({"source": "other.txt"}, "source is owned"),
        ({"task": "segment"}, "task must be detect"),
        ({"mode": "train"}, "mode must be predict"),
        ({"model": "another.pth"}, "weights conflicts"),
    ],
)
def test_native_programmatic_prediction_rejects_ownership_conflicts(
    settings: dict[str, Any], match: str
) -> None:
    runner = build_dependencies(model_preset("rfdetr/small")).model
    with pytest.raises(ValueError, match=match):
        runner.prediction_settings(settings, "best.pth")


def test_native_programmatic_prediction_accepts_matching_explicit_checkpoint() -> None:
    runner = build_dependencies(model_preset("rfdetr/small")).model
    settings = runner.prediction_settings(
        {"model": Path("best.pth"), "source": None, "task": "detect", "mode": "predict"},
        "best.pth",
    )
    assert settings["model"] == "best.pth"
