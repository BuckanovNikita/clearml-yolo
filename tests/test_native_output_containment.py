"""Reject existing native output escapes before backend work or explicit writes."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import CheckpointMetadata, ModelConfig, Preprocessing


@pytest.mark.parametrize("leaf", ["best.pth", "metrics.csv", "nested/plot.png"])
@pytest.mark.parametrize("backend", ["fasterrcnn", "rfdetr", "deimv2"])
def test_detector_output_tree_rejected_before_native_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str, leaf: str
) -> None:
    from clearml_yolo.adapters.deim import backend as deim
    from clearml_yolo.adapters.fasterrcnn import training as fasterrcnn
    from clearml_yolo.adapters.rfdetr import backend as rfdetr
    from clearml_yolo.adapters.torchvision import training as shared_training

    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    output = tmp_path / "workspace" / "native"
    destination = output / leaf
    destination.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_bytes(b"preserve external output")
    destination.symlink_to(outside)

    def native_effect(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Native setup ran before output validation")

    monkeypatch.setattr(shared_training, "training_context", native_effect)
    monkeypatch.setattr(rfdetr, "_names", native_effect)
    monkeypatch.setattr(deim, "_validate_training", native_effect)
    functions = {
        "fasterrcnn": fasterrcnn.train_native, "rfdetr": rfdetr.train, "deimv2": deim.train
    }
    prepared = PreparedDataset(
        data=tmp_path / "input.yaml", ground_truth=tmp_path / "input.csv",
        manifest=tmp_path / "preparation.json", dataset_format="coco", artifacts=[],
    )
    with pytest.raises(ValueError, match="CY_HOME"):
        functions[backend](ModelConfig(), prepared, output, lambda *_args: None)
    assert outside.read_bytes() == b"preserve external output"


def test_checkpoint_leaf_revalidated_before_torch_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.torchvision import training

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    output = tmp_path / "best.pth"
    outside = tmp_path.parent / f"{tmp_path.name}-outside.pth"
    try:
        outside.write_bytes(b"preserve external checkpoint")
        output.symlink_to(outside)
        metadata = CheckpointMetadata(
            backend="fasterrcnn", preset="resnet50_fpn", class_names=("object",),
            preprocessing=Preprocessing(resize="letterbox", size=(608, 960)), dependencies={},
        )
        with pytest.raises(ValueError, match="CY_HOME"):
            training._checkpoint(SimpleNamespace(state_dict=dict), output, 0, 0.5, metadata)
        assert outside.read_bytes() == b"preserve external checkpoint"
    finally:
        outside.unlink(missing_ok=True)


def test_yolo_constructor_validates_output_before_native_initialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.integrations.native_trainer import OwnedDetectionTrainer

    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    output = tmp_path / "workspace" / "native"
    output.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("preserve external args")
    (output / "args.yaml").symlink_to(outside)
    with pytest.raises(ValueError, match="CY_HOME"):
        OwnedDetectionTrainer(overrides={
            "project": str(output.parent), "name": output.name, "exist_ok": True,
            "device": "cpu", "model": "missing.yaml",
        })
    assert outside.read_text() == "preserve external args"
    assert not (output / "weights").exists()


def test_output_tree_checks_contained_directory_alias_without_looping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage.filesystem import validate_output_tree

    workspace = tmp_path / "workspace"
    output = workspace / "native"
    output.mkdir(parents=True)
    shared = workspace / "shared"
    shared.mkdir()
    (output / "alias").symlink_to(shared, target_is_directory=True)
    (shared / "cycle").symlink_to(output, target_is_directory=True)
    monkeypatch.setenv("CY_HOME", str(workspace))
    assert validate_output_tree(output) == output
    outside = tmp_path / "outside"
    outside.write_text("preserved")
    (shared / "escape").symlink_to(outside)
    with pytest.raises(ValueError, match="CY_HOME"):
        validate_output_tree(output)
    assert outside.read_text() == "preserved"


def test_yolo_prediction_checks_actual_native_route_before_stream_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ultralytics.models

    from clearml_yolo.adapters.yolo.inference import predict_on_images
    from native_config_helpers import prediction_config

    workspace = tmp_path / "workspace"
    selected = workspace / "predict2"
    selected.mkdir(parents=True)
    monkeypatch.setenv("CY_HOME", str(workspace))
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"preserve external image")
    (selected / "saved.jpg").symlink_to(outside)

    class Model:
        task = "detect"
        predictor = SimpleNamespace(save_dir=selected, args=SimpleNamespace(), imgsz=[960, 960])
        model = SimpleNamespace(yaml={})

        def __init__(self, _weights: str) -> None:
            self.names: dict[int, str] = {}

        def predict(self, **_kwargs: Any) -> Iterator[Any]:
            def stream() -> Iterator[Any]:
                outside.write_bytes(b"native overwritten image")
                yield SimpleNamespace(path=str(tmp_path / "input.jpg"), boxes=None)
            return stream()

    monkeypatch.setattr(ultralytics.models, "YOLO", Model)
    settings = prediction_config(save=True)
    settings.pop("model")
    settings.pop("source")
    with pytest.raises(ValueError, match="CY_HOME"):
        predict_on_images("input.pt", [str(tmp_path / "input.jpg")], **settings)
    assert outside.read_bytes() == b"preserve external image"
