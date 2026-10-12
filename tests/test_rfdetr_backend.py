"""RF-DETR boundary tests preserve foreground populations and fail-fast recipes."""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from clearml_yolo.application.contracts import PREDICTION_COLUMNS, PreparedDataset
from clearml_yolo.core.models import (
    CheckpointMetadata,
    ModelConfig,
    PredictSettings,
    Preprocessing,
    TrainSettings,
)


def test_rfdetr_background_never_enters_canonical_predictions() -> None:
    from clearml_yolo.adapters.rfdetr.backend import _prediction_frame

    detection = SimpleNamespace(
        xyxy=np.array([[1, 2, 30, 40], [3, 4, 31, 41]]),
        confidence=np.array([0.8, 0.9]),
        class_id=np.array([0, 1]),
    )
    frame = _prediction_frame([("/images/a.png", detection)], ("square",), 300)
    assert list(frame.columns) == PREDICTION_COLUMNS
    assert frame.to_dict("records") == [
        {
            "image_name": "/images/a.png",
            "instance_label": "square",
            "confidence": 0.8,
            "bbox_x_tl": 1.0,
            "bbox_y_tl": 2.0,
            "bbox_x_br": 30.0,
            "bbox_y_br": 40.0,
        }
    ]


def test_rfdetr_limit_applies_after_foreground_filtering() -> None:
    from clearml_yolo.adapters.rfdetr.backend import _prediction_frame

    detection = SimpleNamespace(
        xyxy=np.array([[1, 1, 8, 8], [2, 2, 9, 9], [3, 3, 10, 10]]),
        confidence=np.array([0.99, 0.9, 0.8]),
        class_id=np.array([1, 0, 0]),
    )
    frame = _prediction_frame([("/image.png", detection)], ("square",), 1)
    assert len(frame) == 1
    assert frame.iloc[0]["confidence"] == 0.9


def test_rfdetr_empty_request_retains_population_without_sdk() -> None:
    from clearml_yolo.adapters.rfdetr.backend import predict

    descriptor = CheckpointMetadata(
        backend="rfdetr",
        preset="nano",
        class_names=("square",),
        preprocessing=Preprocessing(resize="stretch", size=64),
    )
    frame = predict(
        ModelConfig(backend="rfdetr", preset="nano"),
        descriptor,
        Path("unused.pth"),
        [],
        PredictSettings(),
    )
    assert frame.empty
    assert frame.attrs["image_paths"] == []
    assert frame.attrs["normalized_imgsz"] == [64, 64]


@pytest.mark.parametrize("requested_size", [None, 128])
def test_rfdetr_reload_preserves_trained_position_grid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requested_size: int | None
) -> None:
    from clearml_yolo.adapters.rfdetr import backend

    checkpoint = tmp_path / "trained-at-64.pth"
    checkpoint.write_bytes(b"SDK checkpoint boundary fixture")
    constructor_args: dict[str, Any] = {}
    prediction_args: dict[str, Any] = {}

    def native_predict(paths: list[str], **kwargs: Any) -> list[Any]:
        prediction_args.update(kwargs)
        return [
            SimpleNamespace(
                xyxy=np.array([[1, 2, 30, 40]]),
                confidence=np.array([0.8]),
                class_id=np.array([0]),
            )
            for _ in paths
        ]

    def constructor(**kwargs: Any) -> Any:
        constructor_args.update(kwargs)
        return SimpleNamespace(predict=native_predict)

    monkeypatch.setattr(backend, "_sdk", lambda: SimpleNamespace(RFDETRNano=constructor))
    monkeypatch.setattr(backend, "_verify_pretrained", lambda *_: None)
    descriptor = CheckpointMetadata(
        backend="rfdetr",
        preset="nano",
        class_names=("0001",),
        preprocessing=Preprocessing(resize="stretch", size=64),
    )
    backend.predict(
        ModelConfig(backend="rfdetr", preset="nano"),
        descriptor,
        checkpoint,
        ["image.jpg"],
        PredictSettings(imgsz=requested_size),
    )
    assert constructor_args["resolution"] == 64
    assert prediction_args["shape"] == (requested_size or 64, requested_size or 64)


def test_rfdetr_explicit_missing_weights_fail_before_native_construction(tmp_path: Path) -> None:
    from clearml_yolo.adapters.rfdetr.backend import train

    config = ModelConfig(
        backend="rfdetr", preset="nano", train=TrainSettings(weights=tmp_path / "missing.pth")
    )
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "gt.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="flat",
        artifacts=[],
    )
    with pytest.raises(FileNotFoundError, match=r"missing\.pth"):
        train(config, prepared, tmp_path / "output", lambda *_: None)


def test_rfdetr_owner_callbacks_keep_finite_metrics_and_native_epochs() -> None:
    from clearml_yolo.adapters.rfdetr.backend import _OwnerMetrics

    events: list[tuple[str, float, int]] = []
    callback = _OwnerMetrics(lambda name, value, epoch: events.append((name, value, epoch)))
    trainer = SimpleNamespace(
        callback_metrics={"loss": np.float32(1.25), "unavailable": float("nan")}, current_epoch=3
    )
    callback.on_train_epoch_end(trainer, None)
    trainer.callback_metrics = {"loss": 0.5, "map": 0.25, "invalid": float("inf")}
    trainer.current_epoch = 4
    callback.on_validation_end(trainer, None)
    assert events == [("loss", 1.25, 3), ("loss", 0.5, 4), ("map", 0.25, 4)]
    assert callback.metrics == {"loss": 0.5, "map": 0.25}


@pytest.mark.parametrize("validation", [False, True])
def test_rfdetr_owner_callback_failure_aborts_native_execution(validation: bool) -> None:
    from clearml_yolo.adapters.rfdetr.backend import _OwnerMetrics

    failure = RuntimeError("owner telemetry rejected")

    def reject(_name: str, _value: float, _epoch: int) -> None:
        raise failure

    callback = _OwnerMetrics(reject)
    hook = callback.on_validation_end if validation else callback.on_train_epoch_end
    with pytest.raises(RuntimeError, match="owner telemetry rejected") as caught:
        hook(SimpleNamespace(callback_metrics={"loss": 1.0}, current_epoch=0), None)
    assert caught.value is failure


def test_rfdetr_missing_native_best_never_falls_back_to_last_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.rfdetr import backend

    data = tmp_path / "data.yaml"
    data.write_text('names: {0: "0001"}\n')
    prepared = PreparedDataset(
        data=data,
        ground_truth=tmp_path / "gt.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="coco",
        artifacts=[],
    )
    output = tmp_path / "output"
    native = SimpleNamespace(model_config=SimpleNamespace(), get_train_config=lambda **_: object())
    monkeypatch.setattr(backend, "_sdk", lambda: SimpleNamespace(RFDETRNano=lambda **_: native))

    def fit(_module: Any, _data: Any) -> None:
        (output / "checkpoint_last.pth").write_bytes(b"unselected native checkpoint")

    monkeypatch.setitem(
        sys.modules,
        "rfdetr.training",
        SimpleNamespace(
            RFDETRModelModule=lambda *_: object(),
            RFDETRDataModule=lambda *_: object(),
            build_trainer=lambda *_, **__: SimpleNamespace(callbacks=[], fit=fit),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytorch_lightning",
        SimpleNamespace(seed_everything=lambda *_, **__: None, Callback=type("Callback", (), {})),
    )
    config = ModelConfig(
        backend="rfdetr", preset="nano", train=TrainSettings(device="cpu", pretrained=False)
    )
    with pytest.raises(RuntimeError, match=r"did not produce checkpoint_best_total\.pth"):
        backend.train(config, prepared, output, lambda *_: None)
    assert (output / "checkpoint_last.pth").read_bytes() == b"unselected native checkpoint"


@pytest.mark.parametrize("settings", [{"iou": 0.3}, {"half": True}])
def test_rfdetr_unsupported_prediction_controls_fail_explicitly(
    settings: dict[str, object],
) -> None:
    from clearml_yolo.adapters.rfdetr.backend import predict

    descriptor = CheckpointMetadata(
        backend="rfdetr",
        preset="nano",
        class_names=("square",),
        preprocessing=Preprocessing(resize="stretch", size=64),
    )
    with pytest.raises(ValueError, match="unsupported"):
        predict(
            ModelConfig(backend="rfdetr", preset="nano"),
            descriptor,
            Path("unused.pth"),
            [],
            PredictSettings.model_validate(settings),
        )


@pytest.mark.parametrize("matches", [True, False])
def test_rfdetr_pretrained_backbone_was_actually_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    matches: bool,
) -> None:
    from clearml_yolo.adapters.rfdetr import backend

    key = "backbone.0.encoder.embeddings.patch_embeddings.projection.weight"
    value = SimpleNamespace(cpu=lambda: [0.25, 0.5])
    checkpoint = tmp_path / "pretrained.pth"
    actual = value if matches else SimpleNamespace(cpu=lambda: [0.0, 0.0])
    native_torch = SimpleNamespace(equal=lambda left, right: left == right)
    native_io = SimpleNamespace(_safe_torch_load=lambda _: {"model": {key: value}})

    def native_module(name: str) -> Any:
        assert name in {"torch", "rfdetr.utilities.io"}
        return native_torch if name == "torch" else native_io

    monkeypatch.setattr(
        "clearml_yolo.adapters.rfdetr.backend.importlib.import_module", native_module
    )
    model = SimpleNamespace(
        model=SimpleNamespace(model=SimpleNamespace(state_dict=lambda: {key: actual}))
    )
    if matches:
        backend._verify_pretrained(model, checkpoint)
    else:
        with pytest.raises(RuntimeError, match="not loaded"):
            backend._verify_pretrained(model, checkpoint)


@pytest.mark.parametrize(
    "changes", [{"resize": "letterbox"}, {"stride": 16}, {"size": [64, 64]}, {"size": 65}]
)
def test_rfdetr_rejects_unsupported_checkpoint_preprocessing(changes: dict[str, Any]) -> None:
    from clearml_yolo.adapters.rfdetr.backend import predict

    preprocessing = Preprocessing.model_validate({"resize": "stretch", "size": 64} | changes)
    descriptor = CheckpointMetadata(
        backend="rfdetr",
        preset="nano",
        class_names=("square",),
        preprocessing=preprocessing,
    )
    with pytest.raises(ValueError, match="preprocessing"):
        predict(
            ModelConfig(backend="rfdetr", preset="nano"),
            descriptor,
            Path("unused.pth"),
            [],
            PredictSettings(),
        )
