"""Enrichment and verification of Ultralytics' native best model."""

import hashlib
import sys
import types
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, override

import pytest

from clearml_yolo.clearml_native import NativeModelError, finalize_native_model


class _Record:
    def __init__(self, model_id: str, checkpoint: Path) -> None:
        self.id = model_id
        self.original_task = "task-id"
        self.task = "task-id"
        self.project = "project-id"
        self.url = f"s3://models/{checkpoint.name}"
        self.local = checkpoint
        self.name = "native"
        self.comment = "native comment"
        self.tags = ["native"]
        self.framework = ""
        self.config_text = ""
        self.labels: dict[str, int] = {}
        self.metadata: dict[str, dict[str, str]] = {}


class _NativeModel:
    records: ClassVar[dict[str, _Record]]

    def __init__(self, model_id: str) -> None:
        self._record = self.records[model_id]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._record, name)

    def get_local_copy(self, **kwargs: Any) -> str:
        assert kwargs == {
            "extract_archive": False,
            "raise_on_error": True,
            "force_download": True,
        }
        return str(self._record.local)

    def get_all_metadata(self) -> dict[str, dict[str, str]]:
        return self._record.metadata


class _OutputModel:
    records: ClassVar[dict[str, _Record]]
    wait_calls: ClassVar[int] = 0
    metadata_result: ClassVar[bool] = True

    def __init__(self, *, base_model_id: str, **kwargs: Any) -> None:
        self._record = self.records[base_model_id]
        self._record.name = kwargs["name"]
        self._record.tags = sorted(kwargs["tags"])
        self._record.comment = "constructor prefix\n" + kwargs["comment"]
        self._record.framework = kwargs["framework"]
        self._record.config_text = kwargs["config_text"]
        self._record.labels = kwargs["label_enumeration"]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._record, name)

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_record":
            object.__setattr__(self, name, value)
        elif name == "comment":
            self._record.comment = value
        else:
            object.__setattr__(self, name, value)

    @classmethod
    def wait_for_uploads(cls) -> None:
        cls.wait_calls += 1

    def set_all_metadata(self, metadata: dict[str, dict[str, str]], *, replace: bool) -> bool:
        assert replace is False
        self._record.metadata.update({key: value | {"key": key} for key, value in metadata.items()})
        return self.metadata_result


class _Task:
    id = "task-id"
    project = "project-id"
    name = "training"
    input_models_id: ClassVar[list[str]] = ["input-model"]

    def __init__(self, records: dict[str, _Record]) -> None:
        self.records = records
        self.flush_calls = 0
        self.reload_calls = 0

    def get_models(self) -> dict[str, list[_NativeModel]]:
        return {"output": [_NativeModel(model_id) for model_id in self.records]}

    def get_tags(self) -> list[str]:
        return ["experiment", "best"]

    def flush(self, *, wait_for_uploads: bool) -> bool:
        assert wait_for_uploads is True
        self.flush_calls += 1
        return True

    def reload(self) -> None:
        self.reload_calls += 1


@pytest.fixture
def native_sdk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[_Task, _Record, Path]:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"checkpoint")
    downloaded = tmp_path / "downloaded.pt"
    downloaded.write_bytes(checkpoint.read_bytes())
    record = _Record("model-id", checkpoint)
    record.local = downloaded
    records = {record.id: record}
    _NativeModel.records = records
    _OutputModel.records = records
    _OutputModel.wait_calls = 0
    _OutputModel.metadata_result = True
    task = _Task(records)
    module = types.ModuleType("clearml")
    module.Model = _NativeModel  # type: ignore[attr-defined]
    module.OutputModel = _OutputModel  # type: ignore[attr-defined]
    model_module = types.ModuleType("clearml.model")
    model_module.Framework = SimpleNamespace(pytorch="PyTorch")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)
    monkeypatch.setitem(sys.modules, "clearml.model", model_module)
    return task, record, checkpoint


def _training_objects(checkpoint: Path) -> tuple[Any, Any]:
    model = SimpleNamespace(
        names={0: "cat", 1: "dog"},
        model=SimpleNamespace(yaml={"backbone": [[-1, 1, "Conv", [64, 3, 2]]], "channels": 3}),
    )
    trainer = SimpleNamespace(
        best=checkpoint,
        args=SimpleNamespace(name="detector", imgsz=960),
    )
    return model, trainer


def test_finalize_enriches_and_registers_the_same_verified_native_model(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    registered: list[Any] = []
    monkeypatch.setattr(
        "clearml_yolo.clearml_native.register_model_barrier",
        lambda owner, verifier: registered.append((owner, verifier)),
    )
    model, trainer = _training_objects(checkpoint)

    model_id = finalize_native_model(task, model, trainer, "yolo11n.pt")

    assert model_id == "model-id"
    assert record.name == "detector"
    assert record.framework == "PyTorch"
    assert record.labels == {"cat": 0, "dog": 1}
    assert set(record.tags) == {"experiment", "best"}
    assert record.comment == "Best checkpoint best.pt produced by task task-id."
    assert "backbone:" in record.config_text
    assert record.metadata["clearml_yolo_checkpoint_role"]["value"] == "best"
    assert record.metadata["clearml_yolo_checkpoint_filename"]["value"] == "best.pt"
    assert (
        record.metadata["clearml_yolo_checkpoint_sha256"]["value"]
        == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    )
    assert record.metadata["clearml_yolo_architecture_reference"]["value"] == "yolo11n.pt"
    assert record.metadata["clearml_yolo_input_model_id"]["value"] == "input-model"
    assert record.metadata["clearml_yolo_input_imgsz"]["value"] == "960"
    assert record.metadata["clearml_yolo_input_channels"]["value"] == "3"
    assert _OutputModel.wait_calls == 1
    assert task.flush_calls == 1
    assert len(registered) == 1
    registered[0][1]()


def test_finalize_rejects_ambiguous_native_outputs(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, _, checkpoint = native_sdk
    other = _Record("other-id", checkpoint)
    task.records[other.id] = other
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="exactly one"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_rejects_failed_native_upload_placeholder(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    record.url = "failed_uploading"
    record.metadata["clearml_yolo_checkpoint_role"] = {"value": "best", "type": "str"}
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="upload"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_rejects_a_download_that_does_not_match_best(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    record.local.write_bytes(b"different")
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="does not match"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_rejects_metadata_update_failure(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, _, checkpoint = native_sdk
    _OutputModel.metadata_result = False
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="metadata"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_rejects_duplicate_label_names(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, _, checkpoint = native_sdk
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)
    model.names = {0: "cat", 1: "cat"}

    with pytest.raises(NativeModelError, match="unique"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_sanitizes_design_and_architecture_reference(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)
    sensitive = "hid" + "den"
    model.model.yaml["token"] = sensitive

    finalize_native_model(
        task,
        model,
        trainer,
        "https://user:pass@example.test/model.pt?token=hidden",
    )

    assert "hidden" not in record.config_text
    architecture = record.metadata["clearml_yolo_architecture_reference"]["value"]
    assert "user:pass" not in architecture
    assert "hidden" not in architecture


def test_unknown_package_version_is_omitted_from_metadata(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from importlib.metadata import PackageNotFoundError

    task, record, checkpoint = native_sdk

    def unavailable(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("clearml_yolo.clearml_native.version", unavailable)
    monkeypatch.setattr("clearml_yolo.clearml_native.register_model_barrier", lambda *_args: None)
    model, trainer = _training_objects(checkpoint)
    finalize_native_model(task, model, trainer, "yolo11n.pt")
    assert not any(key.endswith("_version") for key in record.metadata)


def test_finalize_requires_native_model_registration(
    native_sdk: tuple[_Task, _Record, Path],
) -> None:
    task, _, checkpoint = native_sdk
    task.records.clear()
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match=r"exactly one.*found 0"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


@pytest.mark.parametrize("field", ["original_task", "task", "project"])
def test_finalize_rejects_model_from_another_owner(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    task, record, checkpoint = native_sdk
    monkeypatch.setattr(record, field, "another-owner")
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="not associated"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_finalize_requires_confirmed_flush(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, _, checkpoint = native_sdk
    monkeypatch.setattr(task, "flush", lambda **_kwargs: False)
    model, trainer = _training_objects(checkpoint)

    with pytest.raises(NativeModelError, match="flush"):
        finalize_native_model(task, model, trainer, "yolo11n.pt")


def test_completion_barrier_rechecks_downloaded_best_bytes(
    native_sdk: tuple[_Task, _Record, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    task, record, checkpoint = native_sdk
    barriers: list[Callable[[], None]] = []
    monkeypatch.setattr(
        "clearml_yolo.clearml_native.register_model_barrier",
        lambda _owner, verifier: barriers.append(verifier),
    )
    model, trainer = _training_objects(checkpoint)
    finalize_native_model(task, model, trainer, "yolo11n.pt")

    record.local.write_bytes(b"changed-after-finalization")

    with pytest.raises(NativeModelError, match="does not match"):
        barriers[0]()
    assert checkpoint.read_bytes() == b"checkpoint"
