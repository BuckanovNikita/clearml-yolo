"""GPU selection: NVML/torch index mapping, VRAM scaling and batch divisibility."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from clearml_yolo.gpu import (
    AutoGpuConfig,
    GpuInfo,
    probe_gpus,
    resolve_devices,
    scale_batch_per_gpu,
    select_devices,
)

GIB = 1 << 30


class FakeMemory:
    def __init__(self, total_gb: float, free_gb: float) -> None:
        self.total = int(total_gb * GIB)
        self.free = int(free_gb * GIB)
        self.used = self.total - self.free


class FakeHandle:
    def __init__(self, uuid: str, total_gb: float, free_gb: float, processes: int) -> None:
        self.uuid = uuid
        self.memory = FakeMemory(total_gb, free_gb)
        self.processes = processes


class FakeNVMLError(Exception):
    pass


def make_fake_nvml(handles: list[FakeHandle]) -> types.ModuleType:
    module = types.ModuleType("pynvml")
    module.NVMLError = FakeNVMLError  # type: ignore[attr-defined]
    module.nvmlInit = lambda: None  # type: ignore[attr-defined]
    module.nvmlShutdown = lambda: None  # type: ignore[attr-defined]
    module.nvmlDeviceGetCount = lambda: len(handles)  # type: ignore[attr-defined]
    module.nvmlDeviceGetHandleByIndex = lambda index: handles[index]  # type: ignore[attr-defined]
    module.nvmlDeviceGetUUID = lambda handle: f"GPU-{handle.uuid}"  # type: ignore[attr-defined]
    module.nvmlDeviceGetMemoryInfo = lambda handle: handle.memory  # type: ignore[attr-defined]
    module.nvmlDeviceGetComputeRunningProcesses = (  # type: ignore[attr-defined]
        lambda handle: [object()] * handle.processes
    )
    return module


class FakeProperties:
    def __init__(self, uuid: str, name: str) -> None:
        self.uuid = uuid
        self.name = name


def make_fake_torch(visible_uuids: list[str]) -> types.ModuleType:
    """Emulate torch honouring CUDA_VISIBLE_DEVICES: only these UUIDs are visible."""
    module = types.ModuleType("torch")
    cuda = types.SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: len(visible_uuids),
        get_device_properties=lambda index: FakeProperties(visible_uuids[index], f"GPU{index}"),
    )
    module.cuda = cuda  # type: ignore[attr-defined]
    return module


@pytest.fixture
def patch_modules(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _patch(handles: list[FakeHandle], visible_uuids: list[str]) -> None:
        monkeypatch.setitem(sys.modules, "pynvml", make_fake_nvml(handles))
        monkeypatch.setitem(sys.modules, "torch", make_fake_torch(visible_uuids))

    return _patch


def test_probe_maps_by_uuid_not_index(patch_modules: Any) -> None:
    """With CUDA_VISIBLE_DEVICES=2,3 torch index 0 is the third physical GPU."""
    handles = [
        FakeHandle("aaa", 24.0, 24.0, 0),
        FakeHandle("bbb", 24.0, 24.0, 0),
        FakeHandle("ccc", 40.0, 39.0, 0),
        FakeHandle("ddd", 80.0, 79.0, 0),
    ]
    patch_modules(handles, ["ccc", "ddd"])

    gpus = probe_gpus()

    assert [gpu.uuid for gpu in gpus] == ["ccc", "ddd"]
    assert [gpu.torch_index for gpu in gpus] == [0, 1]
    assert gpus[0].total_vram_gb == pytest.approx(40.0)
    assert gpus[1].total_vram_gb == pytest.approx(80.0)


def test_busy_gpus_are_skipped(patch_modules: Any) -> None:
    handles = [
        FakeHandle("aaa", 24.0, 23.0, 0),
        FakeHandle("bbb", 24.0, 23.0, 2),  # another process is training here
        FakeHandle("ccc", 24.0, 1.0, 0),  # nearly full
    ]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0))

    assert selection.devices == [0]


def test_all_gpus_busy_raises(patch_modules: Any) -> None:
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 1)], ["aaa"])

    with pytest.raises(RuntimeError, match="no free device"):
        select_devices(AutoGpuConfig())


def test_batch_scales_to_smallest_card(patch_modules: Any) -> None:
    """A heterogeneous pair is limited by the smaller card, since DDP splits evenly."""
    handles = [
        FakeHandle("aaa", 48.0, 47.0, 0),
        FakeHandle("bbb", 24.0, 23.0, 0),
    ]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0))

    assert selection.batch_per_gpu == 16
    assert selection.batch == 32
    assert selection.batch % selection.world_size == 0


def test_batch_scales_up_on_larger_cards(patch_modules: Any) -> None:
    handles = [FakeHandle("aaa", 80.0, 79.0, 0), FakeHandle("bbb", 80.0, 79.0, 0)]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0))

    # 16 * 80/24 = 53 -> floored to the power of two below it
    assert selection.batch_per_gpu == 32
    assert selection.batch == 64


def test_scaling_never_drops_below_one() -> None:
    tiny = [
        GpuInfo(
            torch_index=0,
            name="t",
            uuid="u",
            total_vram_gb=2.0,
            free_vram_gb=2.0,
            compute_process_count=0,
        )
    ]

    assert scale_batch_per_gpu(AutoGpuConfig(batch_per_gpu=4, reference_vram_gb=80.0), tiny) == 1


def test_max_gpus_limits_selection(patch_modules: Any) -> None:
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc", "ddd")]
    patch_modules(handles, ["aaa", "bbb", "ccc", "ddd"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, max_gpus=2))

    assert len(selection.devices) == 2
    assert selection.batch == 16


def test_falls_back_to_cpu_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("torch")
    module.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", module)

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8))

    assert selection.devices == "cpu"
    assert selection.batch == 8


def test_explicit_batch_must_divide_by_device_count() -> None:
    disabled = AutoGpuConfig(enabled=False)

    with pytest.raises(ValueError, match="not divisible"):
        resolve_devices(disabled, [0, 1, 2], batch=10)


def test_autobatch_rejected_under_ddp() -> None:
    """batch=-1 is single-GPU only; ultralytics raises deep inside the run otherwise."""
    disabled = AutoGpuConfig(enabled=False)

    with pytest.raises(ValueError, match="single-GPU only"):
        resolve_devices(disabled, [0, 1], batch=-1)


def test_autobatch_allowed_on_single_gpu() -> None:
    selection = resolve_devices(AutoGpuConfig(enabled=False), [0], batch=-1)

    assert selection.devices == [0]
    assert selection.batch == -1
