"""GPU selection: NVML/torch index mapping, admission control, VRAM scaling, batching."""

from __future__ import annotations

import os
import sys
import types
from typing import Any

import pytest
from loguru import logger

from clearml_yolo import gpu as gpu_module
from clearml_yolo.gpu import (
    AutoGpuConfig,
    GpuInfo,
    GpuSurvey,
    probe_gpus,
    resolve_devices,
    resolve_inference_device,
    scale_batch_per_gpu,
    select_devices,
    wait_for_devices,
)

GIB = 1 << 30

# The reserve is a release default, not a property of the selection maths, so tests that
# assert on device counts or batch sizes opt out of it explicitly.
NO_RESERVE = 0


class FakeMemory:
    def __init__(self, total_gb: float, free_gb: float) -> None:
        self.total = int(total_gb * GIB)
        self.free = int(free_gb * GIB)
        self.used = self.total - self.free


class FakeProcess:
    """An NVML compute process, which carries the pid the survey filters on."""

    def __init__(self, pid: int, used_gb: float = 1.0) -> None:
        self.pid = pid
        self.usedGpuMemory = int(used_gb * GIB)  # NVML's own spelling


class FakeHandle:
    def __init__(
        self,
        uuid: str,
        total_gb: float,
        free_gb: float,
        processes: int,
        own_processes: int = 0,
        own_used_gb: float = 1.0,
    ) -> None:
        self.uuid = uuid
        self.memory = FakeMemory(total_gb, free_gb)
        # Foreign pids are negative so they can never collide with this test process.
        self.compute_processes = [FakeProcess(-index - 1) for index in range(processes)]
        self.compute_processes += [FakeProcess(os.getpid(), own_used_gb)] * own_processes


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
        lambda handle: handle.compute_processes
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


@pytest.fixture(autouse=True)
def off_wsl(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Hide the WSL GPU device from every test unless the test asks for it.

    The fallback that counts /dev/dxg holders reads the real machine. Left visible, a
    test whose fake NVML reports an idle card would consult whatever is running on the
    developer's GPU — and, finding it busy, sit in the wait loop until the real process
    exited or the hour-long timeout expired.
    """
    monkeypatch.setattr(gpu_module, "WSL_GPU_DEVICE", tmp_path_factory.mktemp("nodxg") / "dxg")


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

    survey = probe_gpus()

    assert survey.cuda_available
    assert survey.nvml_available
    assert [gpu.uuid for gpu in survey.gpus] == ["ccc", "ddd"]
    assert [gpu.torch_index for gpu in survey.gpus] == [0, 1]
    assert survey.gpus[0].total_vram_gb == pytest.approx(40.0)
    assert survey.gpus[1].total_vram_gb == pytest.approx(80.0)


def test_busy_gpus_are_skipped(patch_modules: Any) -> None:
    handles = [
        FakeHandle("aaa", 24.0, 23.0, 0),
        FakeHandle("bbb", 24.0, 23.0, 2),  # another process is training here
        FakeHandle("ccc", 24.0, 1.0, 0),  # nearly full
    ]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    selection = select_devices(
        AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0, reserve_gpus=NO_RESERVE)
    )

    assert selection.devices == [0]


def test_all_gpus_busy_raises(patch_modules: Any) -> None:
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 1)], ["aaa"])

    with pytest.raises(RuntimeError, match="fewer than 1 usable device"):
        select_devices(AutoGpuConfig(wait_for_free=False))


def test_batch_scales_to_smallest_card(patch_modules: Any) -> None:
    """A heterogeneous pair is limited by the smaller card, since DDP splits evenly."""
    handles = [
        FakeHandle("aaa", 48.0, 47.0, 0),
        FakeHandle("bbb", 24.0, 23.0, 0),
    ]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(
        AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0, reserve_gpus=NO_RESERVE)
    )

    assert selection.batch_per_gpu == 16
    assert selection.batch == 32
    assert selection.batch % selection.world_size == 0


def test_batch_scales_up_on_larger_cards(patch_modules: Any) -> None:
    handles = [FakeHandle("aaa", 80.0, 79.0, 0), FakeHandle("bbb", 80.0, 79.0, 0)]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(
        AutoGpuConfig(batch_per_gpu=16, reference_vram_gb=24.0, reserve_gpus=NO_RESERVE)
    )

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
            foreign_process_count=0,
        )
    ]

    assert scale_batch_per_gpu(AutoGpuConfig(batch_per_gpu=4, reference_vram_gb=80.0), tiny) == 1


def test_max_gpus_limits_selection(patch_modules: Any) -> None:
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc", "ddd")]
    patch_modules(handles, ["aaa", "bbb", "ccc", "ddd"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, max_gpus=2, reserve_gpus=NO_RESERVE))

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


def test_reserve_leaves_a_card_for_other_runs(patch_modules: Any) -> None:
    """Three idle cards, reserve one: training takes two and someone else can still infer."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc")]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, reserve_gpus=1))

    assert len(selection.devices) == 2
    assert selection.batch == 16


def test_reserve_clamps_on_a_single_gpu_host(patch_modules: Any) -> None:
    """The literal policy would leave a one-GPU host unable to ever train."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, reserve_gpus=1))

    assert selection.devices == [0]


def test_reserve_never_starves_the_run_even_when_larger_than_the_host(patch_modules: Any) -> None:
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, reserve_gpus=99))

    assert selection.devices == [0]


def test_max_gpus_and_reserve_compose(patch_modules: Any) -> None:
    """max_gpus is a ceiling and the reserve a floor on the leftovers; the tighter wins."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc", "ddd")]
    patch_modules(handles, ["aaa", "bbb", "ccc", "ddd"])

    assert len(select_devices(AutoGpuConfig(max_gpus=2, reserve_gpus=1)).devices) == 2
    assert len(select_devices(AutoGpuConfig(max_gpus=3, reserve_gpus=2)).devices) == 2


def test_this_runs_own_process_does_not_make_a_card_busy(patch_modules: Any) -> None:
    """The predict stage must be able to reuse the card training just finished on.

    NVML lists the calling process among a card's compute processes, so counting it
    would lock every stage after the first one out of the device it already owns.
    """
    handles = [FakeHandle("aaa", 24.0, 5.0, processes=0, own_processes=1, own_used_gb=18.0)]
    patch_modules(handles, ["aaa"])

    survey = probe_gpus()

    assert survey.gpus[0].foreign_process_count == 0
    assert survey.gpus[0].own_vram_gb == pytest.approx(18.0)
    assert survey.gpus[0].effective_free_vram_gb == pytest.approx(23.0)
    assert select_devices(AutoGpuConfig(batch_per_gpu=8)).devices == [0]


def _warnings_from(action: Any) -> list[str]:
    collected: list[str] = []
    handle = logger.add(lambda message: collected.append(str(message)), level="WARNING")
    try:
        action()
    finally:
        logger.remove(handle)
    return collected


def test_memory_no_local_process_can_explain_is_announced(
    patch_modules: Any, monkeypatch: Any
) -> None:
    """On WSL the occupier is often the Windows host, which this Linux cannot see."""
    monkeypatch.setattr(gpu_module, "_warned_about_blind_process_view", False)
    monkeypatch.setattr(gpu_module, "_wsl_foreign_gpu_processes", lambda _: 0)
    patch_modules([FakeHandle("aaa", 24.0, 6.0, processes=0)], ["aaa"])

    warnings = _warnings_from(probe_gpus)

    assert any("No process on this machine accounts for" in warning for warning in warnings)


def test_wsl_occupancy_comes_from_the_kernel_when_nvml_names_nobody(
    patch_modules: Any, monkeypatch: Any
) -> None:
    """NVML lists no process under WSL, which left max_compute_processes unenforceable."""
    monkeypatch.setattr(gpu_module, "_wsl_foreign_gpu_processes", lambda _: 1)
    patch_modules([FakeHandle("aaa", 24.0, 23.0, processes=0)], ["aaa"])

    survey = probe_gpus()

    assert survey.gpus[0].foreign_process_count == 1
    with pytest.raises(RuntimeError, match="fewer than 1 usable device"):
        select_devices(AutoGpuConfig(wait_for_free=False))


def test_nvmls_own_count_is_never_overridden(patch_modules: Any, monkeypatch: Any) -> None:
    """Where NVML works it is per-card; /dev/dxg is one device shared by every GPU."""
    monkeypatch.setattr(gpu_module, "_wsl_foreign_gpu_processes", lambda _: 7)
    patch_modules([FakeHandle("aaa", 24.0, 23.0, processes=2)], ["aaa"])

    assert probe_gpus().gpus[0].foreign_process_count == 2


def test_this_runs_own_processes_are_not_counted_through_the_wsl_device(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """Otherwise a stage would see its own predecessor and wait for a card it owns."""
    monkeypatch.setattr(gpu_module, "WSL_GPU_DEVICE", tmp_path / "dxg")
    (tmp_path / "dxg").write_bytes(b"")
    monkeypatch.setattr(gpu_module, "_holds_the_wsl_gpu_device", lambda _: True)

    # Every visible pid "holds" the device; only the ones outside this run may count.
    assert gpu_module._wsl_foreign_gpu_processes(os.getpgrp()) is not None


def test_a_host_without_the_wsl_device_is_left_to_nvml(monkeypatch: Any, tmp_path: Any) -> None:
    monkeypatch.setattr(gpu_module, "WSL_GPU_DEVICE", tmp_path / "absent")

    assert gpu_module._wsl_foreign_gpu_processes(None) is None


def test_on_linux_an_idle_card_stays_idle(patch_modules: Any) -> None:
    """Where NVML works, a zero process count is the truth and must not be second-guessed.

    The off_wsl fixture hides the device from the whole suite, so every other test here
    already asserts native-Linux behaviour; this one says so out loud.
    """
    patch_modules([FakeHandle("aaa", 48.0, 47.0, processes=0)], ["aaa"])

    survey = probe_gpus()

    assert survey.gpus[0].foreign_process_count == 0
    assert select_devices(AutoGpuConfig(batch_per_gpu=8)).devices == [0]


def test_an_idle_card_is_not_accused_of_hiding_processes(
    patch_modules: Any, monkeypatch: Any
) -> None:
    """A display allocation is not a neighbour, and warning about it would cry wolf."""
    monkeypatch.setattr(gpu_module, "_warned_about_blind_process_view", False)
    patch_modules([FakeHandle("aaa", 24.0, 23.5, processes=0)], ["aaa"])
    warnings: list[str] = []
    handle = logger.add(lambda message: warnings.append(str(message)), level="WARNING")

    try:
        probe_gpus()
    finally:
        logger.remove(handle)

    assert not any("process-level occupancy" in warning for warning in warnings)


def test_tolerated_foreign_processes_do_not_block(patch_modules: Any) -> None:
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 1)], ["aaa"])

    assert select_devices(AutoGpuConfig(max_compute_processes=1)).devices == [0]


def _survey(free_cards: int) -> GpuSurvey:
    return GpuSurvey(
        cuda_available=True,
        nvml_available=True,
        gpus=[
            GpuInfo(
                torch_index=index,
                name=f"GPU{index}",
                uuid=f"u{index}",
                total_vram_gb=24.0,
                free_vram_gb=23.0,
                foreign_process_count=0 if index < free_cards else 1,
            )
            for index in range(2)
        ],
    )


def test_wait_returns_once_a_card_frees_up() -> None:
    surveys = [_survey(0), _survey(0), _survey(1)]
    slept: list[float] = []

    chosen = wait_for_devices(
        AutoGpuConfig(reserve_gpus=NO_RESERVE, wait_poll_seconds=5.0),
        probe=lambda: surveys.pop(0),
        sleep=slept.append,
        monotonic=lambda: float(len(slept)),
    )

    assert [gpu.torch_index for gpu in chosen] == [0]
    assert slept == [5.0, 5.0]


def test_wait_raises_rather_than_downgrading_to_cpu() -> None:
    clock = iter([0.0, 10.0, 20.0, 30.0, 40.0])

    with pytest.raises(RuntimeError, match="Waited"):
        wait_for_devices(
            AutoGpuConfig(wait_poll_seconds=5.0, wait_timeout_seconds=15.0),
            probe=lambda: _survey(0),
            sleep=lambda _: None,
            monotonic=lambda: next(clock),
        )


def test_unreachable_nvml_raises_instead_of_silently_using_cpu() -> None:
    unreachable = GpuSurvey(cuda_available=True, nvml_available=False)

    with pytest.raises(RuntimeError, match="NVML is unreachable"):
        wait_for_devices(AutoGpuConfig(), probe=lambda: unreachable)

    assert wait_for_devices(
        AutoGpuConfig(cpu_fallback_on_nvml_failure=True), probe=lambda: unreachable
    ) == []


def test_inference_may_use_the_reserved_card(patch_modules: Any) -> None:
    """The reserve exists to protect inference, so inference itself must ignore it."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])

    assert resolve_inference_device(AutoGpuConfig(reserve_gpus=1)) == "0"


def test_inference_falls_back_to_cpu_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("torch")
    module.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", module)

    assert resolve_inference_device(AutoGpuConfig()) == "cpu"
