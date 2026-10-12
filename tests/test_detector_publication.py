"""Native detector publication must create and verify one invocation-owned model."""

import hashlib
import sys
import types
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, cast, override

import pytest

from clearml_yolo.adapters.clearml.native import NativeModelError, owned_native_model
from clearml_yolo.core.models import CheckpointDescriptor, Preprocessing


def test_native_general_redacts_a_copy_and_preserves_nulls_and_defaults(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.detectors import record_detector_arguments

    values: dict[str, Any] = {
        "weights": None,
        "amp": False,
        "workers": 0,
        "classes": [],
        "project": tmp_path,
        "model": {"num_classes": 1, "api_key": "private-model-key"},
        "source": "https://user:password@example.org/data",
    }
    original = deepcopy(values)
    connected: list[dict[str, Any]] = []

    def connect(data: dict[str, Any], *, name: str, ignore_remote_overrides: bool) -> None:
        assert name == "General"
        assert ignore_remote_overrides is True
        connected.append(deepcopy(data))
        # SDK connection objects must not alter the executable or canonical recipe.
        data["workers"] = 99
        data["model"]["num_classes"] = 99

    task = SimpleNamespace(id="owner", connect=connect)
    record_detector_arguments(task, values)
    assert values == original
    assert connected == [
        values
        | {
            "project": str(tmp_path),
            "model": {"num_classes": 1, "api_key": "<redacted>"},
            "source": "https://<redacted>@example.org/data",
        }
    ]


class _Model:
    records: ClassVar[dict[str, Any]] = {}

    def __init__(self, model_id: str) -> None:
        self.record = self.records[model_id]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.record, name)

    def get_all_metadata(self) -> dict[str, dict[str, str]]:
        return cast(dict[str, dict[str, str]], self.record.metadata)

    def get_local_copy(self, **kwargs: Any) -> str:
        assert kwargs == {
            "extract_archive": False,
            "raise_on_error": True,
            "force_download": True,
        }
        return str(self.record.download)


class _Output(_Model):
    constructions: ClassVar[int] = 0
    waits: ClassVar[int] = 0
    metadata_ok: ClassVar[bool] = True
    corrupt: ClassVar[bool] = False

    def __init__(self, **kwargs: Any) -> None:
        assert "base_model_id" not in kwargs
        type(self).constructions += 1
        task = kwargs["task"]
        self.record = SimpleNamespace(
            id="model-id",
            task=task.id,
            original_task=task.id,
            project=task.project,
            name=kwargs["name"],
            config_text=kwargs["config_text"],
            labels=kwargs["label_enumeration"],
            tags=kwargs["tags"],
            comment="prefix\n" + kwargs["comment"],
            framework=kwargs["framework"],
            metadata={},
            url="",
            download=None,
        )
        self.records[self.record.id] = self.record

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"name", "comment"}:
            setattr(self.record, name, value)
        else:
            object.__setattr__(self, name, value)

    def update_weights(self, **kwargs: Any) -> str:
        assert kwargs["auto_delete_file"] is False
        assert kwargs["update_comment"] is False
        local = Path(kwargs["weights_filename"])
        self.record.url = "s3://models/" + kwargs["target_filename"]
        download = local.parent / "downloaded.pth"
        download.write_bytes(b"corrupt" if self.corrupt else local.read_bytes())
        self.record.download = download
        return str(self.record.url)

    def set_all_metadata(self, metadata: dict[str, dict[str, str]], *, replace: bool) -> bool:
        assert replace is False
        self.record.metadata.update({key: dict(value) for key, value in metadata.items()})
        return self.metadata_ok

    @classmethod
    def wait_for_uploads(cls) -> None:
        cls.waits += 1


class _Task:
    id = "task-id"
    project = "project-id"

    def __init__(self) -> None:
        self.flush_ok = True
        self.events: list[dict[str, Any]] = []

    def get_models(self) -> dict[str, list[_Model]]:
        return {"output": [_Model(model_id) for model_id in _Model.records]}

    def get_tags(self) -> list[str]:
        return ["native", "best"]

    def flush(self, *, wait_for_uploads: bool) -> bool:
        assert wait_for_uploads is True
        return self.flush_ok

    def reload(self) -> None:
        pass

    def get_logger(self) -> Any:
        return SimpleNamespace(report_scalar=lambda **kwargs: self.events.append(kwargs))


@pytest.fixture
def sdk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[_Task, Path, CheckpointDescriptor, list[Callable[[], None]]]:
    from clearml_yolo.adapters.clearml import detectors, native

    _Model.records = {}
    _Output.constructions = _Output.waits = 0
    _Output.corrupt = False
    _Output.metadata_ok = True
    module = types.ModuleType("clearml")
    module.Model = _Model  # type: ignore[attr-defined]
    module.OutputModel = _Output  # type: ignore[attr-defined]
    model_module = types.ModuleType("clearml.model")
    model_module.Framework = SimpleNamespace(pytorch="PyTorch")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)
    monkeypatch.setitem(sys.modules, "clearml.model", model_module)
    resources: dict[str, Any] = {}

    def resource(_task: Any, key: str, factory: Callable[[], Any]) -> Any:
        if key not in resources:
            resources[key] = factory()
        return resources[key]

    monkeypatch.setattr(native, "invocation_resource", resource)
    barriers: list[Callable[[], None]] = []
    monkeypatch.setattr(
        detectors, "register_model_barrier", lambda _task, verify: barriers.append(verify)
    )

    def resolve(_task: Any, name: str, **kwargs: Any) -> str:
        kwargs["write_model_name"](name + "-resolved")
        return name + "-resolved"

    monkeypatch.setattr(detectors, "resolve_model_name", resolve)
    weights = tmp_path / "checkpoint_best_total.pth"
    weights.write_bytes(b"native checkpoint")
    descriptor = CheckpointDescriptor(
        backend="rfdetr",
        preset="nano",
        class_names=("square",),
        preprocessing=Preprocessing(resize="stretch", size=64),
        checkpoint_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),
    )
    return _Task(), weights, descriptor, barriers


def test_publisher_verifies_one_model_and_registers_calibration_owner(sdk: tuple[Any, ...]) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    task, weights, descriptor, barriers = sdk
    assert publish_detector_model(task, weights, descriptor, "detector") == "model-id"
    assert _Output.constructions == 1
    assert _Output.waits == 1
    record = _Model.records["model-id"]
    assert record.labels == {"square": 0}
    assert record.name == "detector-resolved"
    assert record.framework == "PyTorch"
    assert "rfdetr" in record.config_text
    assert (
        record.metadata["clearml_yolo_checkpoint_sha256"]["value"] == descriptor.checkpoint_sha256
    )
    assert record.metadata["clearml_yolo_checkpoint_role"]["value"] == "best"
    owned = owned_native_model(task)
    assert owned is not None
    assert owned.model_id == "model-id"
    assert len(barriers) == 1
    record.download.write_bytes(b"changed after upload")
    with pytest.raises(NativeModelError, match="does not match"):
        barriers[0]()


@pytest.mark.parametrize("failure", ["local_hash", "download", "flush", "metadata"])
def test_publisher_rejects_unverified_checkpoint(sdk: tuple[Any, ...], failure: str) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    task, weights, descriptor, barriers = sdk
    if failure == "local_hash":
        weights.write_bytes(b"different checkpoint")
    elif failure == "download":
        _Output.corrupt = True
    elif failure == "flush":
        task.flush_ok = False
    else:
        _Output.metadata_ok = False
    with pytest.raises(NativeModelError):
        publish_detector_model(task, weights, descriptor, "detector")
    assert owned_native_model(task) is None
    assert not barriers
    if failure == "local_hash":
        assert _Output.constructions == 0


def test_publisher_rejects_a_second_output_before_creating_it(sdk: tuple[Any, ...]) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    task, weights, descriptor, _ = sdk
    _Model.records["previous-model"] = SimpleNamespace(id="previous-model")
    with pytest.raises(NativeModelError, match="output model"):
        publish_detector_model(task, weights, descriptor, "detector")
    assert _Output.constructions == 0


def test_metric_reporting_uses_only_owner_task_logger() -> None:
    from clearml_yolo.adapters.clearml.detectors import report_metric

    task = _Task()
    report_metric(task, "train/loss", 0.25, 3)
    assert task.events == [
        {"title": "Native training", "series": "train/loss", "value": 0.25, "iteration": 3}
    ]


def test_published_detector_accepts_verified_calibration_and_barrier_rechecks_it(
    sdk: tuple[Any, ...],
) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model
    from clearml_yolo.adapters.clearml.native import associate_calibration_thresholds

    task, weights, descriptor, barriers = sdk
    publish_detector_model(task, weights, descriptor, "detector")
    associate_calibration_thresholds(
        task,
        {"square": 0.42},
        prediction_checkpoint_sha256=descriptor.checkpoint_sha256,
    )
    record = _Model.records["model-id"]
    assert record.metadata["clearml_yolo_confidence_threshold/square"]["value"] == "0.42"
    record.metadata["clearml_yolo_confidence_threshold/square"]["value"] = "0.9"
    with pytest.raises(NativeModelError, match="custom metadata"):
        barriers[0]()


@pytest.mark.parametrize("field", ["task", "original_task", "project", "labels", "config_text"])
def test_completion_barrier_rechecks_association_and_design(
    sdk: tuple[Any, ...],
    field: str,
) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    task, weights, descriptor, barriers = sdk
    publish_detector_model(task, weights, descriptor, "detector")
    setattr(_Model.records["model-id"], field, "changed")
    with pytest.raises(NativeModelError):
        barriers[0]()


@pytest.mark.parametrize(
    ("backend", "preset"), [("deimv2", "s"), ("rfdetr", "nano"), ("fasterrcnn", "resnet50_fpn")]
)
def test_publisher_preserves_each_native_family_descriptor(
    sdk: tuple[Any, ...],
    backend: str,
    preset: str,
) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    task, weights, descriptor, _ = sdk
    descriptor = CheckpointDescriptor.model_validate(
        descriptor.model_dump() | {"backend": backend, "preset": preset},
    )
    publish_detector_model(task, weights, descriptor, "native")
    metadata = _Model.records["model-id"].metadata
    assert metadata["clearml_yolo_backend"]["value"] == backend
    assert metadata["clearml_yolo_preset"]["value"] == preset
    assert (
        CheckpointDescriptor.model_validate_json(
            metadata["clearml_yolo_checkpoint_descriptor"]["value"],
        )
        == descriptor
    )


def test_publisher_requires_owner_before_creating_model(sdk: tuple[Any, ...]) -> None:
    from clearml_yolo.adapters.clearml.detectors import publish_detector_model

    _, weights, descriptor, _ = sdk
    with pytest.raises(NativeModelError, match="owned task"):
        publish_detector_model(cast(Any, None), weights, descriptor, "native")
    assert _Output.constructions == 0
