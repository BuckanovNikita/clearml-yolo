"""Forced execution validates selectors without project discovery or replacement."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import OmegaConf
from pydantic import ValidationError

from clearml_yolo.adapters.runtime.gpu_scheduling import execution_controls
from clearml_yolo.core.execution import AutoGPUControl


def test_force_defaults_to_false_and_disables_effective_switches() -> None:
    assert AutoGPUControl().force is False
    assert execution_controls({"autogpu": {"force": True}}) == (False, False)


@pytest.mark.parametrize("value", [1, 0, "true", "false", None])
def test_force_is_strict_boolean(value: object) -> None:
    with pytest.raises(ValidationError, match="force"):
        AutoGPUControl.model_validate({"force": value})
    with pytest.raises(TypeError, match="boolean"):
        execution_controls({"autogpu": {"force": value}})


@pytest.mark.parametrize("value", [None, "", "  ", -1, [-1], [], "CUDA", "cuda:-1", [0, 0], True])
def test_force_rejects_nonconcrete_enabled_gpu_selectors(value: object) -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import forced_device_selection

    with pytest.raises(ValueError, match="exact"):
        forced_device_selection("train", {"ultralytics": {"device": value}})


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" CUDA: 2, 0 ", (2, 0)),
        ([2, 0], (2, 0)),
        (" CPU ", "cpu"),
        (" MPS ", "mps"),
        (" MPS:0 ", "mps:0"),
    ],
)
def test_force_preserves_order_and_normalizes_selector_parsing(
    value: object, expected: object
) -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import forced_device_selection

    assert forced_device_selection("train", {"ultralytics": {"device": value}}) == {
        "ultralytics": expected
    }


def test_force_ignores_disabled_phases() -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import forced_device_selection

    assert forced_device_selection(
        "pipeline",
        {"skip_train": True, "ultralytics": {"device": None}, "ultralytics_predict": {"device": 2}},
    ) == {"ultralytics_predict": (2,)}


def test_exact_selection_accepts_same_normalized_selectors_as_force() -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import exact_request

    assert exact_request(
        "train", {"ultralytics": {"device": " CUDA: 2, 0 "}}, ("GPU-a", "GPU-b", "GPU-c")
    ).devices == ("GPU-c", "GPU-a")


def _owner(
    monkeypatch: pytest.MonkeyPatch, replay_device: object = None, *, general: bool = False
) -> tuple[Any, list[object], list[dict[str, Any]]]:
    from clearml_yolo.adapters.clearml import session
    from clearml_yolo.entrypoints.hydra import common

    received: list[object] = []
    records: list[dict[str, Any]] = []

    @contextmanager
    def runtime() -> Iterator[None]:
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        def connect(settings: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            return settings | {"device": replay_device}

        yield SimpleNamespace(running_locally=lambda: not general, connect=connect)

    def replay(task: Any, values: dict[str, Any]) -> dict[str, Any]:
        if replay_device is not None and not general:
            return values | {"ultralytics_predict": {"device": replay_device}}
        return values

    def workflow(
        ultralytics_predict: dict[str, Any],
        clearml: dict[str, Any],
        ultralytics: dict[str, Any] | None = None,
    ) -> None:
        received.append(ultralytics_predict["device"])

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(
        common, "GPUInventory", lambda **kwargs: pytest.fail("NVML inventory initialized")
    )
    monkeypatch.setattr(
        common, "wait_for_available_gpus", lambda *args, **kwargs: pytest.fail("GPU discovery used")
    )
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", replay)
    monkeypatch.setattr(common, "initialize_naming", lambda _: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(
        session, "record_run_configuration", lambda task, values: records.append(values)
    )
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-existing,GPU-other,GPU-last")
    return workflow, received, records


def test_forced_owner_bypasses_probe_preserves_visibility_and_records_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, records = _owner(monkeypatch)
    config = OmegaConf.create(
        {
            "ultralytics_predict": {"device": 2},
            "clearml": {},
            "queue": {"enabled": True},
            "autogpu": {"enabled": True, "force": True},
        }
    )
    common.execute_owned("predict", config, workflow)
    assert received == [2]
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "GPU-existing,GPU-other,GPU-last"
    assert records[0]["execution_policy"]["force"] is True
    assert records[0]["execution_policy"]["queue"] is False
    assert records[1]["gpu_selection"]["effective_devices"] == {"ultralytics_predict": 2}


def test_invalid_force_fails_before_native_or_task_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, _, _ = _owner(monkeypatch)
    monkeypatch.setattr(common, "native_runtime", lambda: pytest.fail("Native runtime initialized"))
    config = OmegaConf.create(
        {"ultralytics_predict": {"device": None}, "clearml": {}, "autogpu": {"force": True}}
    )
    with pytest.raises(ValueError, match="exact"):
        common.execute_owned("predict", config, workflow)


@pytest.mark.parametrize("general", [False, True])
def test_force_replay_cannot_change_devices(monkeypatch: pytest.MonkeyPatch, general: bool) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, _ = _owner(monkeypatch, 1, general=general)
    config = OmegaConf.create(
        {
            "ultralytics_predict": {"device": 2},
            "ultralytics": {"device": 2},
            "clearml": {},
            "autogpu": {"force": True},
        }
    )
    with pytest.raises(ValueError, match="forced device"):
        common.execute_owned("pipeline" if general else "predict", config, workflow)
    assert received == []


def test_force_training_run_replay_cannot_change_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, _ = _owner(monkeypatch)
    monkeypatch.setattr(
        common, "replay_configuration", lambda task, values: values | {"ultralytics": {"device": 1}}
    )
    config = OmegaConf.create(
        {
            "ultralytics": {"device": 2},
            "ultralytics_predict": {"device": 2},
            "clearml": {},
            "autogpu": {"force": True},
        }
    )
    with pytest.raises(ValueError, match="forced device"):
        common.execute_owned("pipeline", config, workflow)
    assert received == []


def test_force_replay_cannot_change_recorded_force(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, _ = _owner(monkeypatch)
    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: values | {"execution_policy": {"force": False}},
    )
    config = OmegaConf.create(
        {"ultralytics_predict": {"device": 2}, "clearml": {}, "autogpu": {"force": True}}
    )
    with pytest.raises(ValueError, match="force"):
        common.execute_owned("predict", config, workflow)
    assert received == []


@pytest.mark.parametrize("device", ["cpu", "mps", " MPS:0 "])
def test_force_cpu_and_mps_need_no_telemetry(monkeypatch: pytest.MonkeyPatch, device: str) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, _ = _owner(monkeypatch)
    config = OmegaConf.create(
        {"ultralytics_predict": {"device": device}, "clearml": {}, "autogpu": {"force": True}}
    )
    common.execute_owned("predict", config, workflow)
    assert received == [device.strip().lower()]


def test_force_forwards_normalized_selector_and_retains_requested_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, records = _owner(monkeypatch)
    config = OmegaConf.create(
        {
            "ultralytics_predict": {"device": " CUDA: 2 "},
            "clearml": {},
            "autogpu": {"force": True},
        }
    )
    common.execute_owned("predict", config, workflow)
    assert received == [2]
    assert records[1]["gpu_selection"]["requested_devices"] == {"ultralytics_predict": " CUDA: 2 "}
    assert records[1]["gpu_selection"]["effective_devices"] == {"ultralytics_predict": 2}


@pytest.mark.parametrize("backend", ["deimv2", "rfdetr", "fasterrcnn"])
@pytest.mark.parametrize(("device", "expected"), [(" CUDA: 2 ", "cuda:2"), (" CPU ", "cpu")])
def test_normalized_force_selectors_are_accepted_by_native_backend_device_handling(
    backend: str, device: str, expected: str
) -> None:
    from clearml_yolo.adapters.deim.backend import _device as deim_device
    from clearml_yolo.adapters.fasterrcnn.inference import execution_device
    from clearml_yolo.adapters.rfdetr.backend import _device as rfdetr_device
    from clearml_yolo.entrypoints.hydra.execution import forced_effective_configuration
    from test_model_scheduling import _config

    requested = OmegaConf.create(_config(backend))
    requested.model.predict.device = device
    effective = forced_effective_configuration("predict", requested)
    converter = {"deimv2": deim_device, "rfdetr": rfdetr_device, "fasterrcnn": execution_device}[
        backend
    ]
    assert str(converter(effective.model.predict.device)) == expected
    assert requested.model.predict.device == device


def test_force_training_preserves_native_order(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    _owner(monkeypatch)
    received: list[object] = []

    def workflow(ultralytics: dict[str, Any], clearml: dict[str, Any]) -> None:
        received.append(ultralytics["device"])

    config = OmegaConf.create(
        {"ultralytics": {"device": [2, 0]}, "clearml": {}, "autogpu": {"force": True}}
    )
    common.execute_owned("train", config, workflow)
    assert received == [[2, 0]]


def test_force_training_replay_cannot_reorder_same_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, _ = _owner(monkeypatch)
    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: values | {"ultralytics": {"device": [0, 2]}},
    )
    config = OmegaConf.create(
        {
            "ultralytics": {"device": [2, 0]},
            "ultralytics_predict": {"device": 2},
            "clearml": {},
            "autogpu": {"force": True},
        }
    )
    with pytest.raises(ValueError, match="forced device"):
        common.execute_owned("pipeline", config, workflow)
    assert received == []


@pytest.mark.parametrize("operation", ["onnx", "build", "verify"])
def test_force_export_requires_concrete_single_selector(operation: str) -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import forced_device_selection

    assert forced_device_selection("export", {"export": {"operation": operation, "device": 2}}) == {
        "export": (2,)
    }
    with pytest.raises(ValueError, match="exact"):
        forced_device_selection("export", {"export": {"operation": operation, "device": "cuda"}})


def test_force_inference_rejects_multiple_gpu_selectors() -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import forced_device_selection

    with pytest.raises(ValueError, match="one exact"):
        forced_device_selection("predict", {"ultralytics_predict": {"device": [2, 0]}})


def test_force_ignores_inherited_project_assignment(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    workflow, received, records = _owner(monkeypatch)
    monkeypatch.setattr(common, "scheduled", lambda: True)
    monkeypatch.setattr(
        common, "assigned_devices", lambda: pytest.fail("Queue assignment consumed")
    )
    monkeypatch.setattr(
        common, "exact_selection", lambda: pytest.fail("Queue identity remapping used")
    )
    config = OmegaConf.create(
        {"ultralytics_predict": {"device": 2}, "clearml": {}, "autogpu": {"force": True}}
    )
    common.execute_owned("predict", config, workflow)
    assert received == [2]
    assert records[1]["gpu_selection"]["reserved_uuids"] == []


@pytest.mark.parametrize("device", [2, None])
def test_forced_prepare_bypasses_live_queue_and_unavailable_nvml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, device: int | None
) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401
    from clearml_yolo.adapters.runtime.gpu_queue import GPUQueue
    from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice
    from clearml_yolo.application.use_cases.predict import predict
    from clearml_yolo.entrypoints.hydra import execution

    class BusyInventory:
        def snapshot(self) -> tuple[GPUDevice, ...]:
            return (GPUDevice("GPU-existing", True),)

    root = tmp_path / "shared-queue"
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(root))
    queue = GPUQueue(inventory=BusyInventory())
    ticket = queue.register(1, ("GPU-existing",))
    try:
        assert ticket.try_acquire() is None
        registry = (root / "registry.json").read_bytes()

        def unavailable_inventory(**kwargs: Any) -> None:
            pytest.fail("Unavailable NVML must never be initialized for force")

        monkeypatch.setattr(execution, "GPUInventory", unavailable_inventory)
        store.add_to_hydra_store(overwrite_ok=True)
        with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
            config = compose(
                config_name="predict",
                return_hydra_config=True,
                overrides=[
                    "queue.enabled=true",
                    "autogpu.enabled=true",
                    "autogpu.force=true",
                    "ground_truth=unused.csv",
                    "weights=unused.pt",
                    f"ultralytics_predict.device={'null' if device is None else device}",
                ],
            )
        job = execution.ModelJob("predict", predict, config)
        if device is None:
            with pytest.raises(ValueError, match="exact"):
                job.prepare()
        else:
            job.prepare()
        assert job.ticket is None
        assert job.queue is None
        assert (root / "registry.json").read_bytes() == registry
    finally:
        ticket.close()
