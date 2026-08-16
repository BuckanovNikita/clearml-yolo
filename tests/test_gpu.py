"""GPU selection: NVML/torch index mapping, admission control, VRAM scaling, batching.

The queue is on by default, so every test here that is not about it says so through the
``unqueued`` fixture below — otherwise a test with a fake NVML behind it would take real
leases in the machine's queue directory, and a test whose cards never free up would wait
there without a deadline for the rest of the developer's afternoon.
"""

from __future__ import annotations

import os
import re
import sys
import types
from collections.abc import Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from clearml_yolo import gpu as gpu_module
from clearml_yolo.gpu import (
    BATCH_TABLE_ENV_VAR,
    AutoGpuConfig,
    DeviceSelection,
    GpuInfo,
    GpuSurvey,
    PeerProcesses,
    probe_gpus,
    remember_batch,
    resolve_devices,
    resolve_inference,
    scale_batch_per_gpu,
    select_devices,
    wait_for_devices,
)
from clearml_yolo.run_queue import QUEUE_DIR_ENV_VAR, QueueConfig, RunQueue

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


@pytest.fixture(autouse=True)
def unremembered(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Point the remembered-batch table at a scratch file for every test.

    Left alone it is a real file in the developer's cache, so a batch some earlier run of
    theirs happened to finish at would answer before the rung under test did — and the
    suite would pass or fail according to what the machine had done that week.
    """
    monkeypatch.setenv(BATCH_TABLE_ENV_VAR, str(tmp_path / "batch_table.json"))


@pytest.fixture(autouse=True)
def unqueued(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Keep the machine's real queue out of every test that does not ask for one.

    ``auto_gpu.queue.enabled`` defaults to true, so without this a test whose fake cards
    are all busy would enqueue in ``/tmp/clearml-yolo`` and wait there with no deadline —
    the queued path has none, deliberately — and a test whose cards are free would leave a
    lease behind for the next developer's run to trip over. Tests about the queue inject
    their own, which goes past the switch this turns off.
    """
    monkeypatch.setattr(gpu_module, "queue_active", lambda _: False)
    monkeypatch.setenv(QUEUE_DIR_ENV_VAR, str(tmp_path / "unused-queue"))
    monkeypatch.setattr(gpu_module, "_peers", PeerProcesses())
    holding_nothing = ExitStack()
    monkeypatch.setattr(gpu_module, "_LEASE_HOLD", holding_nothing)
    yield
    # Restoring the attribute would leave the leases taken during the test held, and their
    # heartbeat threads beating against a directory pytest is about to delete.
    holding_nothing.close()


def queue_for(
    tmp_path: Path, run_id: str = "run-a", user: str = "ann", pid: int = 4242
) -> RunQueue:
    """A queue of this run's own in ``tmp_path``, standing in for the machine's.

    ``pid`` is named rather than read so a lease can claim to be held by a process that is
    not this one, which is what every peer in these tests is.
    """
    return RunQueue(
        QueueConfig(dir=tmp_path / "queue", poll_seconds=1.0),
        run_id=run_id,
        user=user,
        host="box",
        pid=pid,
    )


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

    assert selection.world_size == 2
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


def test_an_explicit_batch_survives_automatic_device_selection(patch_modules: Any) -> None:
    """Waiting for a free card and choosing a batch are separate decisions.

    Folding them together is what left `train.batch` unread on the one path almost every
    run takes: auto_gpu is on by default, and it used to discard the number outright.
    """
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    selection = select_devices(AutoGpuConfig(reserve_gpus=NO_RESERVE), batch=48)

    assert selection.devices == [0, 1]
    assert selection.batch == 48
    assert selection.batch_per_gpu == 24


def test_a_named_device_survives_automatic_batch_selection(patch_modules: Any) -> None:
    """Naming a card and naming a batch are separate decisions, the same way naming a
    batch and letting the cards be surveyed already are.

    Training used to warn and discard a named device whenever auto_gpu was on, while the
    predict stage honoured one — so `device` in a config file meant two different things
    depending on which stage read it, and neither said so.
    """
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc")]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    selection = resolve_devices(AutoGpuConfig(batch_per_gpu=16), [1, 2], batch=None)

    assert selection.devices == [1, 2]
    assert selection.batch == 32
    assert selection.batch_per_gpu == 16


def test_a_named_device_is_spelled_the_way_ultralytics_takes_it(patch_modules: Any) -> None:
    """`device=0,1` is how it arrives from the command line and `[0, 1]` is how DDP wants
    it, so both have to resolve to one request."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    assert resolve_devices(AutoGpuConfig(), "0,1", batch=None).devices == [0, 1]
    assert resolve_devices(AutoGpuConfig(), "cuda:1", batch=None).devices == [1]
    assert resolve_devices(AutoGpuConfig(), 0, batch=None).devices == [0]
    assert resolve_devices(AutoGpuConfig(), "cpu", batch=None).devices == "cpu"


def test_a_named_device_and_a_named_batch_are_both_taken_as_given(patch_modules: Any) -> None:
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    selection = resolve_devices(AutoGpuConfig(), [0, 1], batch=48)

    assert (selection.devices, selection.batch, selection.batch_per_gpu) == ([0, 1], 48, 24)


def test_a_named_device_nvml_cannot_describe_falls_back_to_the_anchor(
    patch_modules: Any,
) -> None:
    """There is no card to size against, so the configured anchor answers rather than a
    number guessed from hardware nobody looked at."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])

    selection = resolve_devices(AutoGpuConfig(batch_per_gpu=8), [7], batch=None)

    assert selection.devices == [7]
    assert selection.batch == 8


def test_an_unset_device_is_still_surveyed_for(patch_modules: Any) -> None:
    """Only a named device is honoured; unset is what hands the choice to the survey."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    selection = resolve_devices(AutoGpuConfig(reserve_gpus=NO_RESERVE), None, batch=None)

    assert selection.devices == [0, 1]


def test_an_explicit_batch_must_still_divide_by_the_cards_chosen_here(patch_modules: Any) -> None:
    """The count was not the user's to know, so the error has to say how to bound it."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc")]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    with pytest.raises(ValueError, match=re.escape("auto_gpu.max_gpus")):
        select_devices(AutoGpuConfig(reserve_gpus=NO_RESERVE), batch=10)


def test_autobatch_is_rejected_against_cards_chosen_here_too(patch_modules: Any) -> None:
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    with pytest.raises(ValueError, match="single-GPU only"):
        select_devices(AutoGpuConfig(reserve_gpus=NO_RESERVE), batch=-1)


def test_a_model_of_its_own_size_gets_a_batch_of_its_own(patch_modules: Any) -> None:
    """The global anchor cannot be right for a yolo11n and a yolo11x at once."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig(
        batch_per_gpu=32, reference_vram_gb=24.0, model_batch_per_gpu={"yolo11x": 8}
    )

    assert select_devices(config, model="yolo11x.pt").batch == 8
    assert select_devices(config, model="yolo11n.pt").batch == 32


def test_a_measured_batch_is_used_as_measured(patch_modules: Any) -> None:
    """A table entry is a number seen to fit, so it is neither scaled nor rounded down.

    80 GiB against a 24 GiB reference would otherwise multiply it, and the power-of-two
    floor would then round the answer away from what was actually measured.
    """
    patch_modules([FakeHandle("aaa", 80.0, 79.0, 0)], ["aaa"])
    config = AutoGpuConfig(
        batch_per_gpu=16, reference_vram_gb=24.0, batch_table={"yolo11m": {"GPU0": 20}}
    )

    assert select_devices(config, model="yolo11m.pt").batch == 20


def test_a_card_is_named_by_any_part_of_what_the_driver_calls_it(patch_modules: Any) -> None:
    """Reproducing a driver string exactly is not something a config should have to do,
    and getting it subtly wrong would look from the outside like having set no table."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig(batch_table={"yolo11m": {"gpu0": 20, "0": 7}})

    # Both keys match "GPU0"; the longer one is the more specific and wins.
    assert select_devices(config, model="yolo11m.pt").batch == 20


def test_a_table_that_does_not_cover_this_many_cards_falls_through(patch_modules: Any) -> None:
    """Guessing across device counts is exactly what the count level exists to prevent."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])
    config = AutoGpuConfig(
        batch_per_gpu=4,
        reference_vram_gb=24.0,
        reserve_gpus=NO_RESERVE,
        batch_table={"yolo11m": {"GPU0": {1: 20}}},
    )

    assert select_devices(config, model="yolo11m.pt", stage="train").batch == 8


def test_a_batch_that_finished_is_remembered_and_read_back(patch_modules: Any) -> None:
    """The point of the file: a number found once by hand is never typed again."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig(batch_per_gpu=4, reference_vram_gb=24.0)

    pinned = select_devices(config, model="yolo11m.pt", batch=48)
    remember_batch(config, "train", "yolo11m.pt", pinned)

    assert select_devices(config, model="yolo11m.pt", stage="train").batch == 48
    # Another stage's evidence is not this one's: inference and training do not hold the
    # same memory, so what one finished at says nothing about the other.
    assert select_devices(config, model="yolo11m.pt", stage="predict").batch == 4


def test_only_the_largest_batch_that_finished_is_kept(patch_modules: Any) -> None:
    """That a small batch fits says nothing; that a large one finished proves the rest."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig(batch_per_gpu=4, reference_vram_gb=24.0)

    for batch in (48, 16):
        remember_batch(
            config, "train", "yolo11m.pt", select_devices(config, model="yolo11m.pt", batch=batch)
        )

    assert select_devices(config, model="yolo11m.pt", stage="train").batch == 48


def test_a_hand_written_table_outranks_what_was_remembered(patch_modules: Any) -> None:
    """The file is a cache; a number the user typed is the authority over it."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig(batch_per_gpu=4, batch_table={"yolo11m": {"GPU0": 12}})

    remember_batch(
        config, "train", "yolo11m.pt", select_devices(config, model="yolo11m.pt", batch=48)
    )

    assert select_devices(config, model="yolo11m.pt", stage="train").batch == 12


def test_nothing_is_remembered_from_a_run_that_surveyed_no_hardware() -> None:
    """A batch with no card to file it under would be read back on a different machine."""
    config = AutoGpuConfig(batch_per_gpu=4)
    unsurveyed = DeviceSelection(devices=[0], batch=64, batch_per_gpu=64)

    remember_batch(config, "train", "yolo11m.pt", unsurveyed)

    assert not gpu_module.batch_table_path().exists()


def test_ultralytics_own_choice_of_batch_is_not_remembered(patch_modules: Any) -> None:
    """batch=-1 is a request, not a measurement; the number it settles on is never seen here."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    config = AutoGpuConfig()

    remember_batch(
        config, "train", "yolo11m.pt", select_devices(config, model="yolo11m.pt", batch=-1)
    )

    assert not gpu_module.batch_table_path().exists()


def test_remembering_can_be_turned_off_in_both_directions(patch_modules: Any) -> None:
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])
    remembering = AutoGpuConfig(batch_per_gpu=4, reference_vram_gb=24.0)
    forgetful = remembering.model_copy(update={"remember_batch": False})

    remember_batch(
        forgetful, "train", "yolo11m.pt", select_devices(forgetful, model="yolo11m.pt", batch=48)
    )
    assert not gpu_module.batch_table_path().exists()

    pinned = select_devices(remembering, model="yolo11m.pt", batch=48)
    remember_batch(remembering, "train", "yolo11m.pt", pinned)
    assert select_devices(forgetful, model="yolo11m.pt", stage="train").batch == 4


def _lock_beside_the_table() -> Path:
    table = gpu_module.batch_table_path()
    return table.with_name(table.name + gpu_module.BATCH_TABLE_LOCK_SUFFIX)


def _finished_on_one_card() -> DeviceSelection:
    return DeviceSelection(devices=[0], batch=16, batch_per_gpu=16, gpus=_survey(1).gpus[:1])


def test_a_batch_is_left_unrecorded_while_another_run_rewrites_the_table(
    monkeypatch: Any,
) -> None:
    """The read and the write are two steps and the table is one file for the machine, so
    two stages finishing together each read it before either wrote — and the second write
    erased the first one's number. Waiting the other run out and then forcing the write
    would be that same lost update; skipping costs one run's worth of measurement."""
    monkeypatch.setattr(gpu_module, "LOCK_WAIT_SECONDS", 0.0)
    _lock_beside_the_table().write_text("another run", encoding="utf-8")

    remember_batch(AutoGpuConfig(), "train", "yolo11m.pt", _finished_on_one_card())

    assert not gpu_module.batch_table_path().exists()


def test_a_lock_no_live_run_ever_released_is_taken_anyway(monkeypatch: Any) -> None:
    """A run killed between claiming the lock and writing the table would otherwise stop
    this machine remembering anything at all until somebody deleted the file by hand."""
    monkeypatch.setattr(gpu_module, "LOCK_WAIT_SECONDS", 0.0)
    lock = _lock_beside_the_table()
    lock.write_text("a run that died holding it", encoding="utf-8")
    os.utime(lock, (0, 0))

    remember_batch(AutoGpuConfig(), "train", "yolo11m.pt", _finished_on_one_card())

    assert gpu_module.batch_table_path().exists()
    assert not lock.exists()


def test_reserve_leaves_a_card_for_other_runs(patch_modules: Any) -> None:
    """Three idle cards, reserve one: training takes two and someone else can still infer."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc")]
    patch_modules(handles, ["aaa", "bbb", "ccc"])

    selection = select_devices(AutoGpuConfig(batch_per_gpu=8, reserve_gpus=1))

    assert selection.world_size == 2
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

    assert select_devices(AutoGpuConfig(max_gpus=2, reserve_gpus=1)).world_size == 2
    assert select_devices(AutoGpuConfig(max_gpus=3, reserve_gpus=2)).world_size == 2


def test_an_exact_request_overrides_the_floor_and_the_ceiling_alike(patch_modules: Any) -> None:
    """num_gpus is "give this run N cards", not "at least N" or "at most N".

    min_devices is a floor that would let the run start on fewer and max_gpus a ceiling it
    would sit under; an exact request has to mean the same thing on both sides.
    """
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb", "ccc", "ddd")]
    patch_modules(handles, ["aaa", "bbb", "ccc", "ddd"])

    assert select_devices(AutoGpuConfig(num_gpus=2, min_devices=1, max_gpus=4)).devices == [0, 1]
    assert select_devices(AutoGpuConfig(num_gpus=3, min_devices=4, max_gpus=1)).devices == [0, 1, 2]


def test_an_exact_request_waits_rather_than_starting_on_fewer_cards(patch_modules: Any) -> None:
    """Half of a two-card run is not a smaller run, it is a differently configured one."""
    handles = [FakeHandle("aaa", 24.0, 23.0, 0), FakeHandle("bbb", 24.0, 1.0, 0)]
    patch_modules(handles, ["aaa", "bbb"])

    with pytest.raises(RuntimeError, match="fewer than 2 usable"):
        select_devices(AutoGpuConfig(num_gpus=2, wait_for_free=False))


def test_the_reserve_steps_aside_for_an_exact_request(patch_modules: Any) -> None:
    """reserve_gpus=1 is exactly why a 4+4 split of eight cards cannot happen today: the
    first run takes N-1 of N. Once a queue is what holds cards back for other runs, holding
    one back again inside the request would make the number the run asked for unreachable."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])

    assert select_devices(AutoGpuConfig(reserve_gpus=1)).devices == [0]
    assert select_devices(AutoGpuConfig(reserve_gpus=1, num_gpus=2)).devices == [0, 1]


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


def _pids_the_proc_filesystem_lists() -> list[int]:
    """Two pids that really are in /proc, which the WSL count walks for itself.

    This process' own pid is left out: it is this run's by definition and would never be
    counted, so it could not tell the two halves of the test apart.
    """
    listed = sorted(
        int(entry.name)
        for entry in Path("/proc").iterdir()
        if entry.name.isdigit() and int(entry.name) != os.getpid()
    )
    return listed[:2]


PEER_GROUP = 90001
OWN_GROUP = 90002


def test_a_peers_process_group_is_subtracted_from_the_wsl_device_count(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """/dev/dxg is one device for every card, so whatever it counts is spread over all of
    them: a peer left in that count marks the very cards the queue has just cleared for
    this run as occupied, which is the hour-long hang a second run on this box sits through.
    The whole group and not the lease's pid alone, because a peer's DDP children each hold
    the device too."""
    monkeypatch.setattr(gpu_module, "WSL_GPU_DEVICE", tmp_path / "dxg")
    (tmp_path / "dxg").write_bytes(b"")
    peer_and_its_child = _pids_the_proc_filesystem_lists()
    monkeypatch.setattr(
        gpu_module, "_holds_the_wsl_gpu_device", lambda pid: pid in peer_and_its_child
    )
    monkeypatch.setattr(
        os, "getpgid", lambda pid: PEER_GROUP if pid in peer_and_its_child else OWN_GROUP
    )

    assert gpu_module._wsl_foreign_gpu_processes(OWN_GROUP) == len(peer_and_its_child)

    monkeypatch.setattr(gpu_module, "_peers", PeerProcesses(groups=frozenset({PEER_GROUP})))

    assert gpu_module._wsl_foreign_gpu_processes(OWN_GROUP) == 0


def test_a_pid_a_peer_lease_names_is_foreign_inside_this_runs_own_group(monkeypatch: Any) -> None:
    """Two runs launched from one shell script share a process group, so each counted the
    other's VRAM as its own and both piled onto the same card. A lease names the pid, which
    is the only thing that tells them apart — and the group rule still has its real job,
    which is not locking a run out of the card its own DDP children already hold."""
    shared_group = 90003
    peer = 90004
    own_child = 90005
    monkeypatch.setattr(os, "getpgid", lambda pid: shared_group)

    counted_as_ours = gpu_module._split_occupancy([FakeProcess(peer, 18.0)], shared_group)
    assert counted_as_ours[0] == 0
    assert counted_as_ours[1] == pytest.approx(18.0)

    monkeypatch.setattr(gpu_module, "_peers", PeerProcesses(pids=frozenset({peer})))

    assert gpu_module._split_occupancy([FakeProcess(peer, 18.0)], shared_group) == (1, 0.0)
    still_ours = gpu_module._split_occupancy([FakeProcess(own_child, 3.0)], shared_group)
    assert still_ours[0] == 0
    assert still_ours[1] == pytest.approx(3.0)


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


def test_a_queued_run_outlives_the_deadline_an_unqueued_one_would_have_had(
    tmp_path: Path,
) -> None:
    """Queue a run behind a three-hour training and an hour-long timeout kills it at the
    one-hour mark, which is the opposite of waiting for a turn. The timeout keeps its
    meaning where it still has one: a wait with nobody keeping the order."""
    config = AutoGpuConfig(reserve_gpus=NO_RESERVE, wait_timeout_seconds=1.0)
    busy_then_free = [_survey(0)] * 20 + [_survey(1)]
    slept: list[float] = []

    chosen = wait_for_devices(
        config,
        probe=lambda: busy_then_free.pop(0),
        sleep=slept.append,
        queue=queue_for(tmp_path),
    )

    assert [gpu.torch_index for gpu in chosen] == [0]
    assert sum(slept) > config.wait_timeout_seconds

    ticks = iter([0.0, 2.0])
    with pytest.raises(RuntimeError, match="Waited"):
        wait_for_devices(
            config,
            probe=lambda: _survey(0),
            sleep=lambda _: None,
            monotonic=lambda: next(ticks),
        )


def test_a_run_arriving_as_a_card_frees_lands_behind_the_ones_already_waiting(
    tmp_path: Path,
) -> None:
    """The queue-jumping hole, and the reason the entries are read before the cards: the
    instant a run releases its card, a run started a second ago sees a free card, never
    enqueues, and takes it in front of everybody who has been waiting for one."""
    peer = queue_for(tmp_path, run_id="run-b", user="bob", pid=4243)
    already_waiting = peer.enqueue(1)
    mine = queue_for(tmp_path)
    slept: list[float] = []

    def let_the_queue_move(seconds: float) -> None:
        slept.append(seconds)
        peer.remove_entry(already_waiting)

    chosen = wait_for_devices(
        AutoGpuConfig(reserve_gpus=NO_RESERVE),
        probe=lambda: _survey(1),
        sleep=let_the_queue_move,
        queue=mine,
    )

    assert [gpu.torch_index for gpu in chosen] == [0]
    # The card was free on the very first survey, and this run still waited its turn.
    assert slept
    assert mine.live_entries() == []


def test_a_card_this_run_already_holds_is_not_queued_for_a_second_time(tmp_path: Path) -> None:
    """The predict stage re-enters the wait holding the card training took. Queued behind a
    peer who can never get past that lease, the run would be waiting for itself."""
    mine = queue_for(tmp_path)
    assert mine.claim_lease(0) is not None
    peer = queue_for(tmp_path, run_id="run-b", user="bob", pid=4243)
    peer.enqueue(1)
    slept: list[float] = []

    chosen = wait_for_devices(
        AutoGpuConfig(reserve_gpus=NO_RESERVE),
        probe=lambda: _survey(0),
        sleep=slept.append,
        queue=mine,
    )

    assert [gpu.torch_index for gpu in chosen] == [0]
    assert slept == []
    assert [entry.run_id for entry in mine.live_entries()] == ["run-b"]


def test_the_lease_file_decides_a_claim_race_and_the_survey_does_not(tmp_path: Path) -> None:
    """Both runs saw the same card free — the window between the survey and the memory
    actually being held is minutes long, which is why the claim is what settles it."""
    mine = queue_for(tmp_path)
    peer = queue_for(tmp_path, run_id="run-b", user="bob", pid=4243)
    surveys = 0

    def probe_while_the_peer_claims() -> GpuSurvey:
        nonlocal surveys
        surveys += 1
        if surveys == 1:
            peer.claim_lease(0)
        if surveys == 2:
            peer.release_lease(0)
        return _survey(1)

    chosen = wait_for_devices(
        AutoGpuConfig(reserve_gpus=NO_RESERVE),
        probe=probe_while_the_peer_claims,
        sleep=lambda _: None,
        queue=mine,
    )

    assert [gpu.torch_index for gpu in chosen] == [0]
    assert mine.live_entries() == []
    # The wait selects *and* claims: the card comes back with this run's lease published on
    # it, which is what closes the minutes-long window a survey on its own leaves open.
    assert [(lease.gpu_index, lease.run_id) for lease in mine.live_leases()] == [(0, "run-a")]


def test_a_run_that_refuses_to_wait_does_not_take_a_place_in_the_queue_either(
    tmp_path: Path,
) -> None:
    """wait_for_free=false is the setting that promises a fast failure, and a queue with no
    deadline in it would turn that same setting into the longest wait of all."""
    mine = queue_for(tmp_path)

    with pytest.raises(RuntimeError, match="Auto GPU mode found"):
        wait_for_devices(
            AutoGpuConfig(wait_for_free=False), probe=lambda: _survey(0), queue=mine
        )

    assert mine.live_entries() == []


def test_a_cancelled_entry_stops_the_run_instead_of_starting_it(tmp_path: Path) -> None:
    """A wait with no deadline needs one way out, and cancelling from cy-queue is it."""
    mine = queue_for(tmp_path)

    def cancel_from_the_viewer(seconds: float) -> None:
        for entry in mine.live_entries():
            mine.remove_entry(entry)

    with pytest.raises(RuntimeError, match="cancelled"):
        wait_for_devices(
            AutoGpuConfig(),
            probe=lambda: _survey(0),
            sleep=cancel_from_the_viewer,
            queue=mine,
        )


def test_inference_may_use_the_reserved_card(patch_modules: Any) -> None:
    """The reserve exists to protect inference, so inference itself must ignore it."""
    patch_modules([FakeHandle("aaa", 24.0, 23.0, 0)], ["aaa"])

    assert resolve_inference(AutoGpuConfig(reserve_gpus=1), None, None).device_name == "0"


def test_inference_falls_back_to_cpu_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("torch")
    module.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", module)

    assert resolve_inference(AutoGpuConfig(), None, None).device_name == "cpu"


def test_a_named_card_is_still_sized_by_the_policy(patch_modules: Any) -> None:
    """The path the pipeline always takes: predict is handed training's own card rather
    than surveying for one, and used to skip the whole batch policy because of it — so a
    table written for this hardware went unread exactly where it was wanted."""
    handles = [FakeHandle(name, 24.0, 23.0, 0) for name in ("aaa", "bbb")]
    patch_modules(handles, ["aaa", "bbb"])
    config = AutoGpuConfig(batch_per_gpu=12, batch_table={"yolo11m": {"GPU1": 20}})

    selection = resolve_inference(config, "1", None, model="yolo11m.pt")

    assert selection.device_name == "1"
    assert selection.batch == 20
    # The card is described, so a run that finishes on it can still be remembered.
    assert [gpu.torch_index for gpu in selection.gpus] == [1]


def test_a_card_that_cannot_be_described_still_gets_a_batch() -> None:
    """No survey means nothing to size against, but inference still needs a number."""
    selection = resolve_inference(AutoGpuConfig(batch_per_gpu=12), "cpu", None)

    assert selection.device_name == "cpu"
    assert selection.batch == 12


def test_a_card_whose_name_is_digits_is_still_a_name() -> None:
    """Hydra reads an unquoted {5090: 20} key as an integer, and its grammar offers no
    quoting that survives there — so the table has to take the key however it arrives."""
    config = AutoGpuConfig.model_validate({"batch_table": {"yolo11m": {5090: 20}}})

    assert config.batch_table == {"yolo11m": {"5090": 20}}


def test_inference_leaves_an_unnamed_card_to_ultralytics_when_the_policy_is_off() -> None:
    """None is not "cpu": with nothing surveyed, the choice stays with ultralytics rather
    than silently becoming the hundredfold slowdown that looks exactly like success."""
    selection = resolve_inference(AutoGpuConfig(enabled=False), None, 8)

    assert selection.device_name is None
    assert selection.batch == 8
