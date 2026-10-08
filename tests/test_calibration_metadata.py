"""Only verified invocation-owned best checkpoints receive calibration metadata."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.adapters.clearml.native import (
    NativeModelError,
    associate_calibration_thresholds,
    finalize_native_model,
    owned_native_model,
)
from test_clearml_native import (
    _OutputModel,
    _Record,
    _Task,
    _training_objects,
)
from test_clearml_native import (
    native_sdk as native_sdk,  # noqa: PLC0414 - shared SDK fixture
)


@pytest.fixture
def owned_model(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> tuple[_Task, _Record, str, list[Callable[[], None]]]:
    task, record, checkpoint = native_sdk
    barriers: list[Callable[[], None]] = []
    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.native.register_model_barrier",
        lambda _owner, callback: barriers.append(callback),
    )
    model, trainer = _training_objects(checkpoint)
    finalize_native_model(task, model, trainer, "yolo11n.pt")
    return task, record, hashlib.sha256(checkpoint.read_bytes()).hexdigest(), barriers


def test_calibration_enriches_same_model_with_exact_readable_class_values(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, record, digest, barriers = owned_model
    identity = (record.id, record.url)
    thresholds = {"cat": 0.12345678901234568, "dog": 1.0}
    associate_calibration_thresholds(task, thresholds, prediction_checkpoint_sha256=digest)
    assert (record.id, record.url) == identity
    assert json.loads(record.metadata["clearml_yolo_confidence_thresholds"]["value"]) == thresholds
    assert record.metadata["clearml_yolo_confidence_threshold/cat"] == {
        "key": "clearml_yolo_confidence_threshold/cat",
        "type": "float",
        "value": repr(thresholds["cat"]),
    }
    assert record.metadata["clearml_yolo_calibration_split"]["value"] == "val"
    assert record.metadata["clearml_yolo_calibration_checkpoint_sha256"]["value"] == digest
    handle = owned_native_model(task)
    assert handle is not None
    assert handle.model_id == identity[0]
    assert len(barriers) == 1
    barriers[0]()


@pytest.mark.parametrize("digest", [None, "", "not-a-hash", "a" * 64])
def test_missing_or_mismatched_prediction_provenance_fails_before_mutation(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]], digest: str | None
) -> None:
    task, record, _, _ = owned_model
    before = dict(record.metadata)
    with pytest.raises(NativeModelError, match=r"provenance|checkpoint"):
        associate_calibration_thresholds(task, {"cat": 0.4}, prediction_checkpoint_sha256=digest)
    assert record.metadata == before


def test_standalone_metrics_has_no_owned_model_and_cannot_associate(
    native_sdk: tuple[_Task, _Record, Path],
) -> None:
    task, record, _ = native_sdk
    assert owned_native_model(task) is None
    with pytest.raises(NativeModelError, match="owned"):
        associate_calibration_thresholds(task, {"cat": 0.4}, prediction_checkpoint_sha256="a" * 64)
    assert record.metadata == {}
    assert record.name == "native"


def test_rejected_metadata_fails(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, _, digest, _ = owned_model
    _OutputModel.metadata_result = False
    with pytest.raises(NativeModelError, match=r"rejected.*calibration"):
        associate_calibration_thresholds(task, {"cat": 0.4}, prediction_checkpoint_sha256=digest)


def test_metadata_readback_is_required_and_checked_again_at_completion(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, record, digest, barriers = owned_model
    associate_calibration_thresholds(task, {"cat": 0.4}, prediction_checkpoint_sha256=digest)
    record.metadata["clearml_yolo_confidence_threshold/cat"]["value"] = "0.3"
    with pytest.raises(NativeModelError, match="custom metadata"):
        barriers[0]()


def test_silently_dropped_metadata_fails_immediate_readback(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task, _, digest, _ = owned_model
    monkeypatch.setattr(_OutputModel, "set_all_metadata", lambda *_args, **_kwargs: True)
    with pytest.raises(NativeModelError, match="custom metadata"):
        associate_calibration_thresholds(task, {"cat": 0.4}, prediction_checkpoint_sha256=digest)


@pytest.mark.parametrize(
    "thresholds", [{}, {"cat": float("nan")}, {"cat": 1.1}, {"": 0.3}, {"cat": True}]
)
def test_invalid_thresholds_fail_before_mutation(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]], thresholds: dict[str, Any]
) -> None:
    task, record, digest, _ = owned_model
    before = dict(record.metadata)
    with pytest.raises(NativeModelError, match=r"threshold|class"):
        associate_calibration_thresholds(task, thresholds, prediction_checkpoint_sha256=digest)
    assert record.metadata == before


def test_test_split_cannot_calibrate_an_owned_model(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, _, digest, _ = owned_model
    with pytest.raises(NativeModelError, match="val"):
        associate_calibration_thresholds(
            task, {"cat": 0.3}, prediction_checkpoint_sha256=digest, split="test"
        )


def test_owned_association_revalidates_stable_model_identity(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, record, digest, _ = owned_model
    record.url = "s3://different/best.pt"
    with pytest.raises(NativeModelError, match="URL changed"):
        associate_calibration_thresholds(task, {"cat": 0.3}, prediction_checkpoint_sha256=digest)


def test_unicode_numeric_labels_and_extreme_precision_are_retained(
    owned_model: tuple[_Task, _Record, str, list[Callable[[], None]]],
) -> None:
    task, record, digest, barriers = owned_model
    thresholds = {"001": 1e-17, "труба/猫": 0.9876543210987654}
    associate_calibration_thresholds(task, thresholds, prediction_checkpoint_sha256=digest)
    assert json.loads(record.metadata["clearml_yolo_confidence_thresholds"]["value"]) == thresholds
    assert record.metadata["clearml_yolo_confidence_threshold/001"]["value"] == "1e-17"
    assert (
        record.metadata["clearml_yolo_confidence_threshold/труба/猫"]["value"]
        == "0.9876543210987654"
    )
    barriers[0]()


def test_finalization_retains_requested_training_name_and_checkpoint_path(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk

    def resolve(_task: Any, name: str, **kwargs: Any) -> str:
        effective_name = name + "-gentle-otter"
        kwargs["write_model_name"](effective_name)
        return effective_name

    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.native.resolve_model_name",
        resolve,
    )
    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.native.register_model_barrier", lambda *_args: None
    )
    model, trainer = _training_objects(checkpoint)
    model_id = finalize_native_model(task, model, trainer, "yolo11n.pt")
    assert model_id == "model-id"
    assert trainer.args.name == "detector"
    assert trainer.best == checkpoint
    assert record.name == "detector-gentle-otter"
    assert record.url == "s3://models/best.pt"
    assert record.metadata["clearml_yolo_requested_model_name"]["value"] == "detector"
    assert record.metadata["clearml_yolo_effective_model_name"]["value"] == "detector-gentle-otter"
