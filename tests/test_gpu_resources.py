"""GPU requests use native device semantics without initializing CUDA in the owner."""

import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from typing import Any, override

import pytest

from clearml_yolo.gpu_resources import (
    GPUDevice,
    GPUInventory,
    device_count,
    execution_devices,
    job_request,
    normalized_device,
)


def test_gpu_device_is_immutable() -> None:
    device = GPUDevice(uuid="GPU-a", busy=False)
    with pytest.raises(FrozenInstanceError):
        device.busy = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 1),
        ("", 1),
        ("  ", 1),
        ("cuda", 1),
        (-1, 1),
        (2, 1),
        ([0, 1], 2),
        ([-1, -1, -1], 3),
        ((3, 7), 2),
        ("0,1", 2),
        ("-1, -1", 2),
        ("cuda:0", 1),
        ("cuda:0,1", 2),
        ("cpu", 0),
        ("mps", 0),
        ("mps:0", 0),
    ],
)
def test_device_count_matches_native_device_selection(value: object, expected: int) -> None:
    assert device_count(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        -2,
        1.5,
        [],
        [0, True],
        [0, -2],
        [0, 1.5],
        "0,,1",
        "cuda:",
        "cuda:0,cuda:1",
        "gpu",
        {"id": 0},
    ],
)
def test_device_count_rejects_ambiguous_or_malformed_values(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="device"):
        device_count(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, [-1]),
        ("cuda", [-1]),
        (2, [-1]),
        ([0, 1], [-1, -1]),
        ("0,1", [-1, -1]),
        ("cuda:0", [-1]),
        ("cuda:0,1", [-1, -1]),
        ("cpu", "cpu"),
        ("mps", "mps"),
        ("mps:0", "mps:0"),
    ],
)
def test_normalized_device_requests_scheduler_selected_gpus(
    value: object, expected: object
) -> None:
    assert normalized_device(value) == expected


def test_execution_devices_are_logical_indices_inside_the_assigned_visibility() -> None:
    assert execution_devices(0) == []
    assert execution_devices(3) == [0, 1, 2]


@pytest.mark.parametrize("count", [-1, True, 1.5])
def test_execution_devices_rejects_invalid_counts(count: object) -> None:
    with pytest.raises((TypeError, ValueError), match="count"):
        execution_devices(count)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("device", "expected"),
    [([0, 1], 2), ("0,1", 2), (2, 1), ([-1, -1], 2), ("cpu", 0)],
)
def test_training_job_request_uses_the_native_training_device(
    device: object, expected: int
) -> None:
    assert job_request("train", {"ultralytics": {"device": device}}) == expected


@pytest.mark.parametrize("command", ["predict", "val"])
@pytest.mark.parametrize(
    ("device", "expected"),
    [([0, 1, 2], 1), ("0,1", 1), (None, 1), ("cpu", 0), ("mps", 0)],
)
def test_inference_job_request_uses_at_most_one_gpu(
    command: str, device: object, expected: int
) -> None:
    config = {"ultralytics_predict": {"device": device}}
    assert job_request(command, config) == expected


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (
            {
                "skip_train": False,
                "skip_predict": False,
                "skip_compare": False,
                "ultralytics": {"device": [0, 1]},
                "ultralytics_predict": {"device": "cpu"},
            },
            2,
        ),
        (
            {
                "skip_train": False,
                "skip_predict": False,
                "skip_compare": True,
                "ultralytics": {"device": "cpu"},
                "ultralytics_predict": {"device": [0, 1]},
            },
            1,
        ),
        (
            {
                "skip_train": True,
                "skip_predict": False,
                "skip_compare": True,
                "ultralytics": {"device": [0, 1]},
                "ultralytics_predict": {"device": [-1, -1]},
            },
            1,
        ),
        (
            {
                "skip_train": True,
                "skip_predict": True,
                "skip_compare": False,
                "ultralytics_predict": {"device": "mps"},
            },
            0,
        ),
        (
            {
                "skip_train": True,
                "skip_predict": True,
                "skip_compare": True,
                "ultralytics_predict": {"device": [0, 1]},
            },
            0,
        ),
    ],
)
def test_pipeline_job_request_follows_the_enabled_gpu_stage(
    config: dict[str, Any], expected: int
) -> None:
    assert job_request("pipeline", config) == expected


@pytest.mark.parametrize(
    ("device", "expected"),
    [([0, 1], 1), ("0,1", 1), ("cpu", 0), ("mps", 0)],
)
def test_standalone_compare_reads_the_native_prediction_device(
    device: object, expected: int
) -> None:
    config = {
        "inference": {"device": "cpu"},
        "ultralytics_predict": {"device": device},
    }
    assert job_request("compare", config) == expected


def test_standalone_compare_demand_uses_only_native_prediction_group() -> None:
    assert job_request("compare", {"inference": {"device": "cpu"}}) == 1


@pytest.mark.parametrize("command", ["metrics", "report", "ground_truth"])
def test_non_gpu_commands_request_no_gpu(command: str) -> None:
    assert job_request(command, {}) == 0


def test_unknown_command_fails_instead_of_silently_requesting_the_wrong_resource() -> None:
    with pytest.raises(ValueError, match="command"):
        job_request("unknown", {})


class _NotSupportedError(RuntimeError):
    pass


class _FakeNVML:
    NVML_DEVICE_MIG_DISABLE = 0
    NVMLError_NotSupported = _NotSupportedError

    def __init__(
        self,
        *,
        uuids: tuple[str, ...],
        processes: tuple[Sequence[object] | BaseException, ...],
        mig_modes: tuple[int | BaseException, ...] | None = None,
    ) -> None:
        self.uuids = uuids
        self.processes = processes
        self.mig_modes = mig_modes or (0,) * len(uuids)
        self.initialized = False
        self.shutdown = False

    def nvmlInit(self) -> None:  # noqa: N802 - mirrors pynvml's public API
        self.initialized = True

    def nvmlShutdown(self) -> None:  # noqa: N802 - mirrors pynvml's public API
        self.shutdown = True

    def nvmlDeviceGetCount(self) -> int:  # noqa: N802 - mirrors pynvml's public API
        assert self.initialized
        return len(self.uuids)

    def nvmlDeviceGetHandleByIndex(  # noqa: N802 - mirrors pynvml's public API
        self, index: int
    ) -> int:
        return index

    def nvmlDeviceGetUUID(self, handle: int) -> str:  # noqa: N802 - pynvml API
        return self.uuids[handle]

    def nvmlDeviceGetMigMode(  # noqa: N802 - mirrors pynvml's public API
        self, handle: int
    ) -> tuple[int, int]:
        value = self.mig_modes[handle]
        if isinstance(value, BaseException):
            raise value
        return value, value

    def nvmlDeviceGetComputeRunningProcesses(  # noqa: N802 - mirrors pynvml's public API
        self, handle: int
    ) -> list[object]:
        value = self.processes[handle]
        if isinstance(value, BaseException):
            raise value
        return list(value)


def _install_nvml(monkeypatch: pytest.MonkeyPatch, fake: _FakeNVML) -> None:
    monkeypatch.setitem(sys.modules, "pynvml", fake)


def test_snapshot_returns_all_physical_gpus_and_marks_external_compute_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeNVML(
        uuids=("GPU-a", "GPU-b", "GPU-c"),
        processes=((), (SimpleNamespace(pid=4711),), ()),
    )
    _install_nvml(monkeypatch, fake)

    assert GPUInventory().snapshot() == (
        GPUDevice(uuid="GPU-a", busy=False),
        GPUDevice(uuid="GPU-b", busy=True),
        GPUDevice(uuid="GPU-c", busy=False),
    )
    assert fake.shutdown


def test_snapshot_reports_unsupported_process_telemetry_as_an_actionable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeNVML(
        uuids=("GPU-a",),
        processes=(_NotSupportedError("unsupported"),),
    )
    _install_nvml(monkeypatch, fake)

    with pytest.raises(RuntimeError, match=r"GPU-a.*process telemetry.*unsupported"):
        GPUInventory().snapshot()
    assert fake.shutdown


def test_snapshot_accepts_hardware_without_mig_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeNVML(
        uuids=("GPU-a",),
        processes=((),),
        mig_modes=(_NotSupportedError("unsupported"),),
    )
    _install_nvml(monkeypatch, fake)

    assert GPUInventory().snapshot() == (GPUDevice(uuid="GPU-a", busy=False),)


def test_snapshot_rejects_mig_enabled_hardware_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeNVML(uuids=("GPU-a",), processes=((),), mig_modes=(1,))
    _install_nvml(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="MIG"):
        GPUInventory().snapshot()
    assert fake.shutdown


def test_snapshot_propagates_unexpected_nvml_errors_and_still_shuts_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenNVML(_FakeNVML):
        @override
        def nvmlDeviceGetUUID(self, handle: int) -> str:
            raise RuntimeError(f"failed UUID for {handle}")

    fake = BrokenNVML(uuids=("GPU-a",), processes=((),))
    _install_nvml(monkeypatch, fake)

    with pytest.raises(RuntimeError, match="failed UUID"):
        GPUInventory().snapshot()
    assert fake.shutdown


class _FixedInventory(GPUInventory):
    def __init__(self, devices: tuple[GPUDevice, ...]) -> None:
        self.devices = devices

    @override
    def snapshot(self) -> tuple[GPUDevice, ...]:
        return self.devices


def test_visible_preserves_cuda_logical_order_independently_of_current_occupancy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(["GPU-c", "GPU-b", "GPU-a"]), stderr=""
    )
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 30.0
        return completed

    monkeypatch.setattr(subprocess, "run", run)
    inventory = _FixedInventory(
        (
            GPUDevice("GPU-a", busy=False),
            GPUDevice("GPU-b", busy=True),
            GPUDevice("GPU-c", busy=False),
        )
    )

    assert inventory.visible() == ("GPU-c", "GPU-b", "GPU-a")
    assert calls
    assert calls[0][0] == sys.executable


def test_visible_rejects_mig_uuid_from_cuda_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(["MIG-instance"]), stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: completed)

    with pytest.raises(RuntimeError, match="MIG"):
        _FixedInventory((GPUDevice("GPU-a", busy=False),)).visible()


def test_visible_reports_probe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        args=[], returncode=3, stdout="", stderr="CUDA initialization failed"
    )
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: completed)

    with pytest.raises(RuntimeError, match="CUDA initialization failed"):
        _FixedInventory((GPUDevice("GPU-a", busy=False),)).visible()


def test_visible_reports_metadata_probe_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired([sys.executable], timeout=30.0)

    monkeypatch.setattr(subprocess, "run", timeout)

    with pytest.raises(RuntimeError, match=r"visibility probe timed out after 30"):
        _FixedInventory((GPUDevice("GPU-a", busy=False),)).visible()


def test_importing_gpu_resources_does_not_start_native_cuda_modules(tmp_path: Path) -> None:
    script = """
import sys
import clearml_yolo.gpu_resources
assert 'torch' not in sys.modules
assert 'ultralytics' not in sys.modules
print('lightweight import')
"""
    result = subprocess.run(  # noqa: S603 - current interpreter and fixed script
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "lightweight import"


def test_visibility_probe_failure_reports_exit_and_redacts_subprocess_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.gpu_resources import _probe_visible_uuids

    def failed_probe(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            ["probe"],
            7,
            stdout="",
            stderr="CUDA unavailable token=private-probe-token",
        )

    monkeypatch.setattr(subprocess, "run", failed_probe)
    with pytest.raises(RuntimeError, match=r"exit 7.*CUDA unavailable") as caught:
        _probe_visible_uuids()
    assert "private-probe-token" not in str(caught.value)
