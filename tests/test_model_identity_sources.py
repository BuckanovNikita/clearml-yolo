"""Source identity follows checkpoint bytes through training and later recovery."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import models as clearml_models
from clearml_yolo.adapters.clearml.native import (
    NativeModelError,
    finalize_native_model,
    owned_native_model,
)
from clearml_yolo.adapters.storage.identity import (
    checkpoint_sha256,
    read_checkpoint_identity,
    write_checkpoint_identity,
)
from clearml_yolo.core.identity import ModelIdentity
from test_clearml_native import _Record, _Task, _training_objects
from test_clearml_native import native_sdk as native_sdk  # noqa: PLC0414 - shared pytest fixture


def test_finalized_name_and_full_training_identity_are_durable(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    monkeypatch.setattr(task, "id", "a" * 32)
    record.task = record.original_task = task.id

    def unique_name(_task: Any, _name: str, **kwargs: Any) -> str:
        kwargs["write_model_name"]("detector-calm-otter")
        return "detector-calm-otter"

    monkeypatch.setattr("clearml_yolo.adapters.clearml.native.resolve_model_name", unique_name)
    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.native.register_model_barrier", lambda *_args: None
    )
    model, trainer = _training_objects(checkpoint)
    finalize_native_model(task, model, trainer, "yolo11n.pt")
    owned = owned_native_model(task)
    assert owned is not None
    assert owned.identity.model_name == "detector-calm-otter"
    assert owned.identity.training_task_id == "a" * 32
    assert owned.identity.checkpoint_sha256 == checkpoint_sha256(checkpoint)
    assert record.metadata["clearml_yolo_training_task_id"]["value"] == task.id
    assert read_checkpoint_identity(checkpoint) == owned.identity
    owned.verify()
    record.metadata["clearml_yolo_training_task_id"]["value"] = "reporting-task"
    with pytest.raises(NativeModelError, match="metadata"):
        owned.verify()


def test_local_identity_rejects_changed_weights(tmp_path: Path) -> None:
    path = tmp_path / "best.pt"
    path.write_bytes(b"trained")
    identity = ModelIdentity(model_name="detector", checkpoint_sha256=checkpoint_sha256(path))
    write_checkpoint_identity(path, identity)
    path.write_bytes(b"replacement")
    with pytest.raises(ValueError, match="does not match"):
        clearml_models.resolve_weights_with_identity(path)


def test_recovery_preserves_original_training_task_in_foreign_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"trained")
    metadata = {
        "clearml_yolo_checkpoint_role": "best",
        "clearml_yolo_effective_model_name": "unique-trained-model",
        "clearml_yolo_training_task_id": "a" * 32,
        "clearml_yolo_checkpoint_sha256": checkpoint_sha256(checkpoint),
    }
    source = SimpleNamespace(
        id="source-model",
        name="old-name",
        original_task="a" * 32,
        url="https://files.example/best.pt",
        get_metadata=metadata.get,
        get_local_copy=lambda: str(checkpoint),
    )
    task = SimpleNamespace(
        id="b" * 32,
        name="foreign-report",
        artifacts={},
        get_models=lambda: {"output": [source]},
        get_output_log_web_page=lambda: "url",
    )
    monkeypatch.setattr(clearml_models, "_task", lambda _: task)
    path, identity = clearml_models.resolve_weights_with_identity(task.id)
    assert path == checkpoint
    assert identity is not None
    assert identity.model_name == "unique-trained-model"
    assert identity.training_task_id == "a" * 32
    assert "b" * 32 not in identity.caption
    assert "a" * 32 in identity.caption
    metadata["clearml_yolo_checkpoint_sha256"] = "wrong-hash"
    with pytest.raises(ValueError, match="SHA-256"):
        clearml_models.resolve_weights_with_identity(task.id)
    metadata["clearml_yolo_training_task_id"] = "c" * 32
    with pytest.raises(ValueError, match="original task"):
        clearml_models.resolve_weights_with_identity(task.id)


def test_legacy_artifact_identity_has_no_invented_model_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"legacy")
    task = SimpleNamespace(
        id="a" * 32,
        name="legacy-training",
        artifacts={"best.pt": SimpleNamespace(get_local_copy=lambda: str(checkpoint))},
        get_models=lambda: {"output": []},
        get_output_log_web_page=lambda: "url",
    )
    monkeypatch.setattr(clearml_models, "_task", lambda _: task)
    _, identity = clearml_models.resolve_weights_with_identity(task.id)
    assert identity is not None
    assert identity.model_name == task.name
    assert identity.training_task_id == task.id
    assert identity.model_id is None


def test_model_uri_identity_recovers_without_reporting_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sys
    import types

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"remote")
    downloads: list[str] = []

    def download() -> str:
        downloads.append("weights")
        return str(checkpoint)

    model = SimpleNamespace(
        id="remote-model",
        name="remote-detector",
        original_task="a" * 32,
        get_local_copy=download,
        get_metadata=lambda _: None,
    )
    sdk = types.ModuleType("clearml")
    sdk.Model = lambda model_id: model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", sdk)
    path, identity = clearml_models.resolve_weights_with_identity("clearml://remote-model")
    assert path == checkpoint
    assert identity is not None
    assert identity.model_name == "remote-detector"
    assert identity.training_task_id == "a" * 32
    assert identity.model_id == model.id
    assert downloads == ["weights"]
