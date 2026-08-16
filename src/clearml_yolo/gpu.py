"""Automatic GPU selection, admission control and model-aware batch sizing.

GPUs are surveyed through NVML rather than torch because NVML needs no CUDA context:
``torch.cuda.mem_get_info`` allocates roughly half a gigabyte on every device it probes,
which would occupy the very memory the survey is trying to measure.

A run does not merely pick devices, it waits for them and then claims them: starting
training on a host whose cards are busy either crashes or evicts someone else's inference,
and a card that was merely *seen* free is one a peer may take in the minutes before the
memory is actually held. ``reserve_gpus`` leaves cards behind for other runs to infer on,
the wait loop holds the run at the door until enough cards are free, and a lease file
taken through :mod:`clearml_yolo.run_queue` is what closes the window between the two.
With the queue in front of the cards the wait also becomes a queue: entries are read
before the survey, only the head of the order may claim, and a run that has taken its
place in line waits for its turn however long that is.

The batch a run lands on comes from the first of five sources that can answer, and which
one did is always logged, because a number arrived at silently is a number nobody can
correct. In order: the batch the stage was given outright, the ``batch_table`` this
hardware was measured into, the batch a previous run of this stage was seen to finish at
(:func:`remember_batch`), a per-model anchor scaled by the card's VRAM, and finally the
one global anchor scaled the same way. The first three are measurements and are used as
they stand; the last two are a batch at a reference card, so both go through the ratio.
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from itertools import takewhile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from clearml_yolo.run_queue import (
    NO_PID,
    Entry,
    Lease,
    QueueConfig,
    RunQueue,
    _create_exclusive,
    order,
    queue_active,
    queue_dir,
)

BYTES_PER_GIB = 1 << 30

# Where a batch that ran to completion is written down. An absolute path in the
# environment wins, so a shared machine can keep one table per user or per project.
BATCH_TABLE_ENV_VAR = "CLEARML_YOLO_BATCH_TABLE"
DEFAULT_BATCH_TABLE = Path.home() / ".cache" / "clearml-yolo" / "batch_table.json"
# What a stage falls back to when nothing surveyed the hardware: no card was named, so
# there is nothing to size a batch against.
DEFAULT_BATCH = 16

# ``model -> card -> batch``, where the batch is either one number for any device count
# or a mapping from device count to number. Written by hand into ``batch_table``, and by
# :func:`remember_batch` into the file above under one further key naming the stage.
BatchTable = dict[str, dict[str, int | dict[int, int]]]


class AutoGpuConfig(BaseModel):
    """Policy for picking devices and deriving a total batch size from them."""

    enabled: bool = True
    batch_per_gpu: int = Field(default=16, ge=1)
    reference_vram_gb: float = Field(default=24.0, gt=0)
    # The same anchor as above, but per model, because a yolo11x and a yolo11n do not fit
    # the same card the same way. Keyed by the name of the weights without their suffix.
    model_batch_per_gpu: dict[str, int] = Field(default_factory=dict)
    # Batches measured on this hardware rather than estimated from it, so they are used
    # exactly as written — neither scaled to VRAM nor rounded to a power of two.
    batch_table: BatchTable = Field(default_factory=dict)
    # Whether a batch that ran to completion is written down and read back next time.
    remember_batch: bool = True

    @field_validator("batch_table", "model_batch_per_gpu", mode="before")
    @classmethod
    def _a_card_called_5090_is_a_name(cls, table: Any) -> Any:
        """Take the model and card keys as names however they were spelled.

        Hydra reads an unquoted ``{5090: 20}`` key as an integer, and its override grammar
        accepts no quoting that survives in that position — so without this the table
        would be refused for exactly those cards whose names are digits.

        Mapping rather than dict, because a table that came through Hydra arrives as an
        omegaconf node: it behaves like a mapping and is not one by type.
        """
        if not isinstance(table, Mapping):
            return table
        return {
            str(model): {str(card): batch for card, batch in by_card.items()}
            if isinstance(by_card, Mapping)
            else by_card
            for model, by_card in table.items()
        }
    min_free_vram_gb: float = Field(default=8.0, ge=0)
    # Workstations with an attached display idle around 10% VRAM before any training
    # starts, so a stricter threshold would reject every local GPU.
    max_used_fraction: float = Field(default=0.25, ge=0, le=1)
    max_gpus: int | None = None
    # "Give this run N cards and let the queue say which" — an exact count, so it overrides
    # both the min_devices floor and the max_gpus ceiling, and reserve_gpus stops applying:
    # holding cards back for other runs is the queue's job once there is a queue, and it is
    # precisely reserve_gpus=1 that makes a 4+4 split of eight cards impossible. Left unset,
    # the min_devices/max_gpus/reserve_gpus ladder decides exactly as it did before.
    num_gpus: int | None = Field(default=None, ge=1)
    scale_to_vram: bool = True
    round_to_power_of_two: bool = True
    # Cards left untouched so inference belonging to other runs keeps somewhere to go.
    # Clamped during selection: a host with one GPU would otherwise never train.
    reserve_gpus: int = Field(default=1, ge=0)
    min_devices: int = Field(default=1, ge=1)
    # Foreign compute processes tolerated per card. Processes belonging to this run are
    # never counted here, so a stage that follows training on the same device is not
    # locked out by training's own leftover context.
    max_compute_processes: int = Field(default=0, ge=0)
    wait_for_free: bool = True
    wait_poll_seconds: float = Field(default=30.0, gt=0)
    # The deadline of a run waiting with no queue in front of it, where a card still busy
    # after an hour is held by something nobody is going to hand over. A queued run has no
    # deadline at all: queue it behind a three-hour training and this would kill it at the
    # one-hour mark, which is the opposite of waiting for a turn.
    wait_timeout_seconds: float = Field(default=3600.0, gt=0)
    # Where this run takes its place in line, and how it is recognised as still alive.
    # Nested here rather than beside auto_gpu because the wait is where it is read, and the
    # wait is reached from train, predict and compare — all three of which are already
    # handed auto_gpu by the pipeline.
    queue: QueueConfig = Field(default_factory=QueueConfig)
    # CPU is never the way out of a wait: a transient NVML failure would otherwise turn
    # a GPU run into a silent hundredfold slowdown. Hosts with no CUDA at all still fall
    # back to CPU regardless of this flag.
    cpu_fallback_on_nvml_failure: bool = False


class GpuInfo(BaseModel):
    """A physical GPU as seen by NVML, already matched to its torch index."""

    torch_index: int
    name: str
    uuid: str
    total_vram_gb: float
    free_vram_gb: float
    foreign_process_count: int
    own_vram_gb: float = 0.0

    @property
    def effective_free_vram_gb(self) -> float:
        """Free VRAM, counting what this run itself already holds as available."""
        return self.free_vram_gb + self.own_vram_gb

    @property
    def used_fraction(self) -> float:
        return 1.0 - self.effective_free_vram_gb / self.total_vram_gb

    @property
    def unattributed_vram_gb(self) -> float:
        """VRAM in use that belongs to no compute process NVML is willing to name."""
        return max(0.0, self.total_vram_gb - self.free_vram_gb - self.own_vram_gb)


class GpuSurvey(BaseModel):
    """One NVML sweep, keeping the reason an empty result is empty.

    Collapsing "this host has no CUDA" and "NVML could not be reached" into an empty
    list would make a transient probe failure indistinguishable from a CPU-only
    machine, and the wait loop would exit into CPU training on both.
    """

    cuda_available: bool
    nvml_available: bool
    gpus: list[GpuInfo] = Field(default_factory=list)


class DeviceSelection(BaseModel):
    """What the run should be handed: devices plus a divisible batch.

    ``devices`` is None when nothing chose one, which is not the same as ``"cpu"``: it
    leaves the choice with ultralytics, as a stage that surveyed no hardware must.
    """

    devices: list[int] | str | None
    batch: int
    batch_per_gpu: int
    gpus: list[GpuInfo] = Field(default_factory=list)

    @property
    def world_size(self) -> int:
        return len(self.devices) if isinstance(self.devices, list) else 1

    @property
    def device_name(self) -> str | None:
        """The single device string ultralytics takes for inference: ``"0"``, ``"cpu"``."""
        if not isinstance(self.devices, list):
            return self.devices
        return str(self.devices[0]) if self.devices else "cpu"


def _decode(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _nvml_handles_by_uuid(pynvml: Any) -> dict[str, Any]:
    handles: dict[str, Any] = {}
    for index in range(pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)
        handles[_decode(pynvml.nvmlDeviceGetUUID(handle))] = handle
    return handles


def _own_process_group() -> int | None:
    try:
        return os.getpgrp()
    except OSError:
        return None


class PeerProcesses(BaseModel):
    """The processes of the runs holding the other cards, as their leases name them.

    A process group used to be the whole answer to "is this one of mine", and it is the
    wrong answer twice: two runs launched from one shell script share a group, so each
    counted the other's VRAM as its own and both piled onto the same card. A lease names
    the pid that took it, which is what separates them.
    """

    pids: frozenset[int] = frozenset()
    # The peer's DDP children, reached through the group rather than named one by one,
    # because each of them holds VRAM and a WSL device handle of its own. This run's own
    # group is deliberately never in here: in the shared-shell case it *is* the peer's
    # group, and disowning our own children would lock this run out of its own card.
    groups: frozenset[int] = frozenset()

    def covers(self, pid: int) -> bool:
        """Whether this process belongs to a run that holds a lease on another card."""
        if pid in self.pids:
            return True
        if not self.groups:
            return False
        try:
            return os.getpgid(pid) in self.groups
        except (ProcessLookupError, PermissionError):
            return False


# The survey is reached through a zero-argument seam, so what the queue knows about its
# peers is left here for the survey to read rather than threaded down through it. Empty
# whenever the queue is off, which is what leaves an unqueued run's behaviour untouched.
_peers = PeerProcesses()


def _belongs_to_this_run(pid: int, own_group: int | None) -> bool:
    """Whether a compute process is this process or one of its DDP children.

    A process some peer's lease accounts for is that peer's however it was launched: the
    process group cannot tell two runs started from one shell apart, and a lease can.
    """
    if pid == os.getpid():
        return True
    if _peers.covers(pid):
        return False
    if own_group is None:
        return False
    try:
        return os.getpgid(pid) == own_group
    except (ProcessLookupError, PermissionError):
        return False


def _split_occupancy(processes: Sequence[Any], own_group: int | None) -> tuple[int, float]:
    """Count foreign compute processes and total the VRAM this run already holds.

    NVML reports the calling process among the compute processes of the card it is
    using. Counting it would make a run consider its own device busy the moment it
    probes a second time — which is exactly what the predict stage does after training.
    """
    foreign = 0
    own_bytes = 0
    for process in processes:
        if _belongs_to_this_run(int(process.pid), own_group):
            # NVML reports None for processes whose per-process usage it cannot read.
            own_bytes += int(process.usedGpuMemory or 0)
        else:
            foreign += 1
    return foreign, own_bytes / BYTES_PER_GIB


def probe_gpus() -> GpuSurvey:
    """Describe every GPU torch can see, reading live memory figures from NVML.

    Devices are matched by UUID because NVML ignores ``CUDA_VISIBLE_DEVICES`` while
    torch honours it, so identical indices routinely denote different cards.
    """
    import torch

    if not torch.cuda.is_available():
        logger.warning("CUDA is unavailable; no GPUs to probe")
        return GpuSurvey(cuda_available=False, nvml_available=False)

    try:
        import pynvml
    except ImportError:
        logger.warning("nvidia-ml-py is not installed; cannot inspect GPU memory")
        return GpuSurvey(cuda_available=True, nvml_available=False)

    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError as error:
        logger.warning("NVML initialisation failed ({}); cannot inspect GPU memory", error)
        return GpuSurvey(cuda_available=True, nvml_available=False)

    own_group = _own_process_group()
    try:
        by_uuid = _nvml_handles_by_uuid(pynvml)
        gpus: list[GpuInfo] = []
        for torch_index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(torch_index)
            bare_uuid = str(properties.uuid)
            handle = by_uuid.get(f"GPU-{bare_uuid}") or by_uuid.get(bare_uuid)
            if handle is None:
                logger.warning(
                    "No NVML device matches torch device {} (uuid {}); skipping it",
                    torch_index,
                    bare_uuid,
                )
                continue
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            foreign, own_vram_gb = _split_occupancy(
                pynvml.nvmlDeviceGetComputeRunningProcesses(handle), own_group
            )
            gpus.append(
                GpuInfo(
                    torch_index=torch_index,
                    name=properties.name,
                    uuid=bare_uuid,
                    total_vram_gb=memory.total / BYTES_PER_GIB,
                    free_vram_gb=memory.free / BYTES_PER_GIB,
                    foreign_process_count=foreign,
                    own_vram_gb=own_vram_gb,
                )
            )
        _count_processes_the_way_wsl_allows(gpus, own_group)
        _warn_if_process_view_is_blind(gpus)
        return GpuSurvey(cuda_available=True, nvml_available=True, gpus=gpus)
    finally:
        pynvml.nvmlShutdown()


# Display and compositor allocations sit well under this; a training run does not.
BLIND_PROCESS_VIEW_GIB = 1.0
# WSL routes every GPU client through this one paravirtualisation device, so a process
# holding it open is a process using the GPU.
WSL_GPU_DEVICE = Path("/dev/dxg")
_warned_about_blind_process_view = False


def _holds_the_wsl_gpu_device(pid: int) -> bool:
    try:
        return any(
            descriptor.readlink() == WSL_GPU_DEVICE
            for descriptor in Path(f"/proc/{pid}/fd").iterdir()
        )
    except OSError:
        # The process exited mid-scan, or belongs to another user whose descriptors are
        # not ours to read. Either way it cannot be counted.
        return False


def _wsl_foreign_gpu_processes(own_group: int | None) -> int | None:
    """Count GPU-using processes the way WSL still allows, or None when not on WSL.

    NVML returns an empty process list under WSL however busy the card is, which makes
    ``max_compute_processes`` silently unenforceable — a user who asks for an exclusive
    card gets whatever is free by VRAM alone. The kernel still knows: every WSL GPU
    client holds ``/dev/dxg`` open.

    A run whose lease is known is subtracted here, whole process group and all, because the
    count that comes back is spread across every card: leaving a peer in it would mark the
    cards the queue has just cleared for this run as occupied too, which is the hour-long
    hang a second run on this box used to sit through.
    """
    if not WSL_GPU_DEVICE.exists():
        return None
    foreign = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if _belongs_to_this_run(pid, own_group) or _peers.covers(pid):
            continue
        if _holds_the_wsl_gpu_device(pid):
            foreign += 1
    return foreign


def _count_processes_the_way_wsl_allows(gpus: list[GpuInfo], own_group: int | None) -> None:
    """Fill in occupancy from the kernel when NVML named nobody at all.

    Only when NVML named nobody: where it works, it is per-card and authoritative, while
    ``/dev/dxg`` is one device shared by every GPU, so the count it yields cannot be
    attributed to a particular card.
    """
    if any(gpu.foreign_process_count for gpu in gpus):
        return
    foreign = _wsl_foreign_gpu_processes(own_group)
    if not foreign:
        return
    if len(gpus) > 1:
        logger.warning(
            "{} GPU process(es) found through {} but WSL shares one device across all "
            "{} cards, so every card is treated as occupied",
            foreign,
            WSL_GPU_DEVICE,
            len(gpus),
        )
    for gpu in gpus:
        gpu.foreign_process_count = foreign


def _warn_if_process_view_is_blind(gpus: list[GpuInfo]) -> None:
    """Say so when nothing can account for the memory a card is holding.

    On WSL the occupied memory is usually the Windows host's — a desktop, a browser, a
    game — which no process inside this Linux has a handle on. That is unknowable from
    here, so the VRAM thresholds are what stands between the run and a shared card.
    """
    global _warned_about_blind_process_view  # noqa: PLW0603  warn once per process
    if _warned_about_blind_process_view:
        return
    blind = [
        gpu
        for gpu in gpus
        if not gpu.foreign_process_count and gpu.unattributed_vram_gb > BLIND_PROCESS_VIEW_GIB
    ]
    if not blind:
        return
    _warned_about_blind_process_view = True
    logger.warning(
        "No process on this machine accounts for the {} in use on GPU(s) {} — it belongs "
        "to another user, or to the host outside WSL. auto_gpu.max_compute_processes "
        "cannot see such a neighbour; min_free_vram_gb and max_used_fraction are what "
        "guard against sharing the card.",
        ", ".join(f"{gpu.unattributed_vram_gb:.1f} GiB" for gpu in blind),
        [gpu.torch_index for gpu in blind],
    )


def _is_available(gpu: GpuInfo, config: AutoGpuConfig) -> bool:
    if gpu.foreign_process_count > config.max_compute_processes:
        logger.info(
            "GPU {} ({}) is busy: {} foreign compute process(es), limit {}",
            gpu.torch_index,
            gpu.name,
            gpu.foreign_process_count,
            config.max_compute_processes,
        )
        return False
    if gpu.effective_free_vram_gb < config.min_free_vram_gb:
        logger.info(
            "GPU {} ({}) is full: {:.1f} GiB free, need {:.1f}",
            gpu.torch_index,
            gpu.name,
            gpu.effective_free_vram_gb,
            config.min_free_vram_gb,
        )
        return False
    if gpu.used_fraction > config.max_used_fraction:
        logger.info(
            "GPU {} ({}) is full: {:.1%} of VRAM already used, limit {:.1%}",
            gpu.torch_index,
            gpu.name,
            gpu.used_fraction,
            config.max_used_fraction,
        )
        return False
    return True


def _apply_reserve(available: list[GpuInfo], config: AutoGpuConfig) -> list[GpuInfo]:
    """Take the freest cards, leaving ``reserve_gpus`` behind for other runs.

    ``max_gpus`` is a ceiling ("use at most N") and the reserve is a floor on what is
    left over ("leave at least N"), so both fold into one slice. The reserve is clamped
    to keep at least one device: taken literally on a single-GPU host it would leave
    every run with nothing, forever.
    """
    if not available:
        return []

    ceiling = config.max_gpus if config.max_gpus is not None else len(available)
    after_reserve = len(available) - config.reserve_gpus
    keep = min(ceiling, max(1, after_reserve))
    if config.reserve_gpus and keep > after_reserve:
        logger.warning(
            "reserve_gpus={} would leave this run no device among {} free card(s); "
            "taking {} and reserving none",
            config.reserve_gpus,
            len(available),
            keep,
        )

    freest_first = sorted(available, key=lambda gpu: gpu.free_vram_gb, reverse=True)
    return sorted(freest_first[:keep], key=lambda gpu: gpu.torch_index)


def _requested_devices(config: AutoGpuConfig) -> int:
    """How many cards this run has to hold before it may start."""
    return config.min_devices if config.num_gpus is None else config.num_gpus


def _selectable(
    survey: GpuSurvey,
    config: AutoGpuConfig,
    *,
    wanted: int,
    unavailable: frozenset[int] = frozenset(),
) -> list[GpuInfo]:
    """The cards this run may take: usable, not under a lease, and no more than it asked.

    ``num_gpus`` is an exact request, so it decides the count outright and the reserve and
    the ceiling stop applying. Without it ``wanted`` is not consulted at all, because
    ``min_devices`` is a floor on what is enough rather than a cap on what is taken and a
    four-card host still trains on all four.
    """
    available = [
        gpu
        for gpu in survey.gpus
        if gpu.torch_index not in unavailable and _is_available(gpu, config)
    ]
    if config.num_gpus is None:
        return _apply_reserve(available, config)
    freest_first = sorted(available, key=lambda gpu: gpu.free_vram_gb, reverse=True)
    return sorted(freest_first[:wanted], key=lambda gpu: gpu.torch_index)


def _no_device_message(config: AutoGpuConfig, total: int, waited: float | None) -> str:
    preamble = (
        f"Waited {waited:.0f}s and still found"
        if waited is not None
        else "Auto GPU mode found"
    )
    return (
        f"{preamble} fewer than {_requested_devices(config)} usable device(s) among "
        f"{total} GPU(s): "
        f"every card is busy, holds less than {config.min_free_vram_gb} GiB free, or is "
        f"held back by reserve_gpus={config.reserve_gpus}. Lower auto_gpu.min_free_vram_gb, "
        "raise auto_gpu.max_used_fraction or auto_gpu.max_compute_processes, drop "
        "auto_gpu.reserve_gpus, extend auto_gpu.wait_timeout_seconds, or set an explicit device."
    )


# Cards are held for as long as the process lives rather than for one stage: predict runs
# on the card training has just used, and a lease given back in between is a lease a peer
# takes. Closing the stack releases every one of them; the heartbeat inside ``holding`` is
# what lets a peer recover them when the process is killed before it can.
_LEASE_HOLD = ExitStack()
atexit.register(_LEASE_HOLD.close)


def wait_for_devices(
    config: AutoGpuConfig,
    *,
    probe: Callable[[], GpuSurvey] = probe_gpus,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    queue: RunQueue | None = None,
) -> list[GpuInfo]:
    """Block until this run may hold the cards it asked for, and claim them before returning.

    An empty list means the host has no usable GPU at all and the caller should run on
    CPU. Every other outcome raises: a wait must never end by quietly downgrading the
    run to CPU, which is a hundredfold slowdown that looks exactly like success.

    With the queue on, the wait is a place in line and the cards come back claimed; with it
    off, it is the deadline-bounded poll it has always been. ``probe``, ``sleep``,
    ``monotonic`` and ``queue`` are injected so the whole policy is testable without a GPU,
    without real time passing and without a queue directory on this machine.
    """
    waiting_room = queue if queue is not None else _queue_for(config)
    if waiting_room is None:
        return _wait_alone(config, probe=probe, sleep=sleep, monotonic=monotonic)
    return _wait_in_turn(config, waiting_room, probe=probe, sleep=sleep)


def _queue_for(config: AutoGpuConfig) -> RunQueue | None:
    """This machine's queue, or None when this run is not to take a place in it.

    A queue directory that cannot be built is worth a warning and not a dead run: the
    selection that happens without one is the one every release so far has shipped.
    """
    if not queue_active(config.queue):
        return None
    try:
        # The run's name here has to be stable for the whole process, so that a later stage
        # recognises the leases an earlier one took, and unique among the runs alive on the
        # machine, which host and pid together are.
        return RunQueue(config.queue, run_id=f"{socket.gethostname()}-{os.getpid()}")
    except OSError as error:
        logger.warning(
            "Cannot use the run queue at {} ({}); this run picks its cards without one",
            queue_dir(config.queue),
            error,
        )
        return None


def _surveyed(config: AutoGpuConfig, probe: Callable[[], GpuSurvey]) -> GpuSurvey | None:
    """One sweep of the hardware, or None when this run is to fall back to CPU."""
    survey = probe()
    if not survey.cuda_available:
        return None
    if survey.nvml_available:
        return survey
    if config.cpu_fallback_on_nvml_failure:
        logger.warning("NVML is unreachable; falling back to CPU as configured")
        return None
    raise RuntimeError(
        "NVML is unreachable, so GPU occupancy cannot be measured and this run "
        "would silently train on CPU. Install nvidia-ml-py, or set "
        "auto_gpu.cpu_fallback_on_nvml_failure=true to accept that."
    )


def _wait_alone(
    config: AutoGpuConfig,
    *,
    probe: Callable[[], GpuSurvey],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
) -> list[GpuInfo]:
    """Wait for cards with nobody keeping the order, on ``wait_timeout_seconds``.

    The deadline means something here that it cannot mean for a queued run: with no queue
    behind this run, a card still busy after an hour is held by something that is not going
    to hand it over, and saying so beats waiting for ever.
    """
    started = monotonic()
    while True:
        survey = _surveyed(config, probe)
        if survey is None:
            return []

        needed = _requested_devices(config)
        selectable = _selectable(survey, config, wanted=needed)
        if len(selectable) >= needed:
            return selectable

        elapsed = monotonic() - started
        if not config.wait_for_free:
            raise RuntimeError(_no_device_message(config, len(survey.gpus), waited=None))
        remaining = config.wait_timeout_seconds - elapsed
        if remaining <= 0:
            raise RuntimeError(_no_device_message(config, len(survey.gpus), waited=elapsed))

        logger.info(
            "Waiting for {} free GPU(s): {} of {} usable, {:.0f}s elapsed, {:.0f}s before timeout",
            needed,
            len(selectable),
            len(survey.gpus),
            elapsed,
            remaining,
        )
        sleep(min(config.wait_poll_seconds, remaining))


def _peer_processes(leases: Sequence[Lease], own_run_id: str) -> PeerProcesses:
    """The pids and process groups of the runs holding the other cards.

    ``NO_PID`` is skipped rather than looked up: it is what a lease that has been claimed
    but not yet written says, and ``os.getpgid(0)`` answers with this run's own group,
    which would make every process on the machine look like somebody else's.
    """
    pids = {
        lease.pid for lease in leases if lease.run_id != own_run_id and lease.pid != NO_PID
    }
    own_group = _own_process_group()
    groups = set()
    for pid in pids:
        try:
            group = os.getpgid(pid)
        except (ProcessLookupError, PermissionError):
            continue
        if group != own_group:
            groups.add(group)
    return PeerProcesses(pids=frozenset(pids), groups=frozenset(groups))


def _at_the_head(entry: Entry | None, waiting: Sequence[Entry], queue: RunQueue) -> bool:
    """Whether it is this run's turn: nobody is queueing at all, or the order starts here.

    Ranking the entries that were read *before* the survey is the whole point of reading
    them first. A run not yet in the queue may only go straight through when the queue is
    empty — never because the cards happen to look free, which is how a run started a
    second ago would take a card off everybody who has been waiting for one.
    """
    if entry is None:
        return not waiting
    ranked = order(waiting, queue.served_mtimes())
    return bool(ranked) and ranked[0].run_id == entry.run_id


def _claimed(queue: RunQueue, held: list[GpuInfo], wanted: list[GpuInfo]) -> list[GpuInfo]:
    """Take leases on the cards that are not this run's yet, or come back empty-handed.

    The lease file is the arbiter of a race and the survey is not: two runs that both saw
    the same card free are separated here, and the loser gives back whatever it took and
    surveys again rather than starting on a card somebody else now holds.
    """
    taken = queue.claim_leases([gpu.torch_index for gpu in wanted])
    if not taken:
        logger.info("Another run claimed a card first; looking again")
        return []
    _LEASE_HOLD.enter_context(queue.holding([lease.gpu_index for lease in taken]))
    queue.mark_served()
    return sorted(held + wanted, key=lambda gpu: gpu.torch_index)


def _announce_position(entry: Entry, waiting: Sequence[Entry], queue: RunQueue) -> None:
    ranked = order(waiting, queue.served_mtimes())
    ahead = [
        f"{other.user}:{other.run_id} ({other.num_gpus} GPU)"
        for other in takewhile(lambda other: other.run_id != entry.run_id, ranked)
    ]
    logger.info(
        "Queued for {} GPU(s) at position {} of {}; ahead of this run: {}",
        entry.num_gpus,
        len(ahead) + 1,
        len(ranked),
        ", ".join(ahead) or "nobody — every card is busy",
    )


def _wait_in_turn(
    config: AutoGpuConfig,
    queue: RunQueue,
    *,
    probe: Callable[[], GpuSurvey],
    sleep: Callable[[float], None],
) -> list[GpuInfo]:
    """Take a place in line, wait for the head of it, and claim the cards on arriving there.

    There is no deadline: a run queued behind a three-hour training waits three hours, and
    ``cy-queue`` cancelling its entry is the way out. The cards this run already holds are
    answered with before anything else, because a stage that queued for a card its own
    process is holding would wait for a peer that can never get past it.
    """
    global _peers  # noqa: PLW0603  the survey seam below takes nothing to pass this through

    needed = _requested_devices(config)
    entry: Entry | None = None
    try:
        while True:
            waiting = queue.live_entries()
            leases = queue.live_leases()
            _peers = _peer_processes(leases, queue.run_id)
            survey = _surveyed(config, probe)
            if survey is None:
                return []

            mine = frozenset(
                lease.gpu_index for lease in leases if lease.run_id == queue.run_id
            )
            held = [gpu for gpu in survey.gpus if gpu.torch_index in mine]
            if len(held) >= needed:
                logger.info("Reusing GPU(s) this run already holds a lease on: {}", sorted(mine))
                return held[:needed]

            under_lease = frozenset(lease.gpu_index for lease in leases)
            free = _selectable(
                survey, config, wanted=needed - len(held), unavailable=under_lease
            )
            if _at_the_head(entry, waiting, queue) and len(held) + len(free) >= needed:
                cards = _claimed(queue, held, free)
                if cards:
                    return cards

            if not config.wait_for_free:
                # "Do not wait" has to mean not taking a place in line either, or the one
                # setting that promises a fast failure becomes the slowest wait of all.
                raise RuntimeError(_no_device_message(config, len(survey.gpus), waited=None))
            if entry is None:
                entry = queue.enqueue(needed)
                logger.info(
                    "Taking a place in the queue at {} as entry {} for {} GPU(s)",
                    queue.dir,
                    entry.seq,
                    needed,
                )
                continue
            if not queue.heartbeat_entry(entry):
                raise RuntimeError(
                    f"This run's queue entry {entry.seq} is gone, so it was cancelled from "
                    "cy-queue while it waited for GPU(s). Nothing was started."
                )
            _announce_position(entry, waiting, queue)
            sleep(queue.config.poll_seconds)
    finally:
        if entry is not None:
            queue.remove_entry(entry)


def _floor_power_of_two(value: int) -> int:
    return 1 << (value.bit_length() - 1) if value > 0 else 1


def scale_batch_per_gpu(
    config: AutoGpuConfig, gpus: list[GpuInfo], anchor: int | None = None
) -> int:
    """Fit a per-GPU batch measured at ``reference_vram_gb`` to the smallest selected card.

    DDP splits the total batch evenly, so the weakest device sets the ceiling for
    every device. ``anchor`` names the batch to scale, which is the model's own when the
    config gives one for it and the global ``batch_per_gpu`` otherwise.
    """
    reference = config.batch_per_gpu if anchor is None else anchor
    if not config.scale_to_vram or not gpus:
        return reference

    smallest_vram = min(gpu.total_vram_gb for gpu in gpus)
    scaled = int(reference * smallest_vram / config.reference_vram_gb)
    if config.round_to_power_of_two:
        scaled = _floor_power_of_two(scaled)
    scaled = max(1, scaled)
    if scaled != reference:
        logger.info(
            "Scaled batch per GPU {} -> {} ({:.1f} GiB smallest card vs {:.1f} GiB reference)",
            reference,
            scaled,
            smallest_vram,
            config.reference_vram_gb,
        )
    return scaled


def _normalised(text: str) -> str:
    return " ".join(text.split()).lower()


def model_key(model: str | None) -> str | None:
    """The name a batch table is keyed by: ``weights/yolo11m.pt`` becomes ``yolo11m``."""
    if not model:
        return None
    return _normalised(Path(model).stem)


def _entry_for_card(by_card: dict[str, Any], card: str) -> Any:
    """The entry whose key names this card, taking the most specific key that matches.

    Keys match as substrings of the name the driver reports, so ``5090`` and ``rtx 5090``
    both find ``NVIDIA GeForce RTX 5090``. Reproducing a driver string exactly is not
    something a config should have to do, and getting it subtly wrong would look from the
    outside exactly like having set no table at all.
    """
    reported = _normalised(card)
    matching = [key for key in by_card if _normalised(key) in reported]
    if not matching:
        return None
    return by_card[max(matching, key=lambda key: len(_normalised(key)))]


def table_batch(table: dict[str, Any], model: str | None, card: str, world_size: int) -> int | None:
    """Look a per-GPU batch up in ``model -> card -> device count``.

    The device count may be left out, written as a bare number against the card, which
    means the batch holds however many devices the run gets.
    """
    by_card = table.get(model) if model else None
    if not by_card:
        return None
    entry = _entry_for_card(by_card, card)
    if entry is None:
        return None
    if isinstance(entry, int):
        return entry
    by_count = {int(count): int(batch) for count, batch in entry.items()}
    if world_size not in by_count:
        logger.info(
            "A batch table names {} on {} but not for {} device(s); looking further down",
            model,
            card,
            world_size,
        )
        return None
    return by_count[world_size]


def batch_table_path() -> Path:
    return Path(os.environ.get(BATCH_TABLE_ENV_VAR) or DEFAULT_BATCH_TABLE)


def _remembered_batches() -> dict[str, Any]:
    """Every batch previously seen to finish, keyed by stage. Empty if there are none."""
    path = batch_table_path()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        logger.warning("Cannot read the remembered batch table {} ({}); ignoring it", path, error)
        return {}
    return loaded if isinstance(loaded, dict) else {}


def select_batch_per_gpu(
    config: AutoGpuConfig, model: str | None, gpus: list[GpuInfo], stage: str
) -> int:
    """The per-GPU batch for this model on these cards, saying which source answered."""
    smallest = min(gpus, key=lambda gpu: gpu.total_vram_gb)
    key = model_key(model)
    world_size = len(gpus)

    measured = table_batch(config.batch_table, key, smallest.name, world_size)
    if measured is not None:
        logger.info(
            "Batch per GPU {} from auto_gpu.batch_table for {} on {} x {}",
            measured,
            key,
            world_size,
            smallest.name,
        )
        return measured

    if config.remember_batch:
        finished = table_batch(
            _remembered_batches().get(stage, {}), key, smallest.name, world_size
        )
        if finished is not None:
            logger.info(
                "Batch per GPU {} remembered from a {} run of {} that finished on {} x {}",
                finished,
                stage,
                key,
                world_size,
                smallest.name,
            )
            return finished

    anchor = config.model_batch_per_gpu.get(key) if key else None
    if anchor is not None:
        logger.info(
            "Batch per GPU anchored at {} for {} by auto_gpu.model_batch_per_gpu", anchor, key
        )
    return scale_batch_per_gpu(config, gpus, anchor)


def _refuse_indivisible_batch(batch: int, world_size: int, *, chosen_here: bool) -> None:
    """Reject a total batch that DDP would silently shrink.

    Ultralytics floor-divides the total across ranks without checking, so an indivisible
    batch trains on fewer images per step than the run asked for — a quiet difference
    between the experiment that was configured and the one that ran.
    """
    if world_size <= 1:
        return
    remedy = (
        f"Cap the run with auto_gpu.max_gpus, or give a batch that is a multiple of {world_size}"
        if chosen_here
        else f"Set an explicit batch that is a multiple of {world_size}, or enable auto_gpu"
    )
    if batch < 1:
        raise ValueError(
            f"batch={batch} requests ultralytics AutoBatch, which is single-GPU only, but "
            f"{world_size} devices were given. {remedy}."
        )
    if batch % world_size:
        raise ValueError(
            f"batch={batch} is not divisible by {world_size} devices; ultralytics would "
            f"silently train on {batch // world_size * world_size} images per step. {remedy}."
        )


def select_devices(
    config: AutoGpuConfig,
    model: str | None = None,
    stage: str = "train",
    batch: int | None = None,
) -> DeviceSelection:
    """Choose the devices to run on and the total batch size to pass to YOLO.

    The returned batch is always a multiple of the device count: ultralytics treats
    ``batch`` as the total across ranks and floor-divides it by world size without
    checking divisibility, silently shrinking the effective batch otherwise.

    A ``batch`` given here is honoured rather than discarded. Waiting for free cards and
    picking a batch are separate decisions, and folding them together is what left the
    configured ``batch`` unread on the one path almost every run takes.
    """
    chosen = wait_for_devices(config)
    if not chosen:
        on_cpu = config.batch_per_gpu if batch is None else batch
        logger.warning("No GPU on this host; falling back to CPU with batch {}", on_cpu)
        return DeviceSelection(devices="cpu", batch=on_cpu, batch_per_gpu=on_cpu)

    devices = [gpu.torch_index for gpu in chosen]
    if batch is None:
        batch_per_gpu = select_batch_per_gpu(config, model, chosen, stage)
        total = batch_per_gpu * len(devices)
    else:
        _refuse_indivisible_batch(batch, len(devices), chosen_here=True)
        total = batch
        batch_per_gpu = batch // len(devices) if batch > 0 else batch

    logger.info(
        "Auto GPU selected devices {} — {} x {} = total batch {}",
        devices,
        len(devices),
        batch_per_gpu,
        total,
    )
    return DeviceSelection(
        devices=devices, batch=total, batch_per_gpu=batch_per_gpu, gpus=chosen
    )


def _card_behind(device: str) -> list[GpuInfo]:
    """Describe the card a device string names, without waiting for it.

    A stage that follows training in one process is handed training's own card rather
    than surveying for one, because this process still holds that card's memory and a
    survey would wait for a device the run already owns. The card still has to be
    described — otherwise the whole batch policy stops at the one path the pipeline
    always takes, and a table written for this hardware would go unread there.
    """
    index = device.removeprefix("cuda:")
    if not index.isdigit():
        return []
    return [gpu for gpu in probe_gpus().gpus if gpu.torch_index == int(index)]


def _named_devices(device: list[int] | int | str) -> list[int] | str:
    """Spell a requested device the way ultralytics and torch both take it.

    ``"0"`` and ``"0,1"`` are how a device reaches this from the command line, and
    ``[0, 1]`` is how ultralytics wants a multi-GPU run named, so the two are the same
    request written differently and have to resolve to one thing. Anything that is not a
    list of CUDA ordinals — ``"cpu"``, ``"mps"`` — is passed through as it stands.
    """
    if isinstance(device, int):
        return [device]
    if isinstance(device, list):
        return device
    parts = [part.strip().removeprefix("cuda:") for part in device.split(",")]
    if parts and all(part.isdigit() for part in parts):
        return [int(part) for part in parts]
    return device


def _cards_behind(devices: list[int] | str) -> list[GpuInfo]:
    """Describe every card a requested device list names, without waiting for any."""
    if not isinstance(devices, list):
        return []
    by_index = {gpu.torch_index: gpu for gpu in probe_gpus().gpus}
    found = [by_index[index] for index in devices if index in by_index]
    return found if len(found) == len(devices) else []


def resolve_inference(
    auto_gpu: AutoGpuConfig | None,
    device: str | None,
    batch: int | None,
    model: str | None = None,
    stage: str = "predict",
) -> DeviceSelection:
    """Name the one card a stage infers on and the batch it infers at.

    Inference cannot go through :func:`resolve_devices`: digital-metrics takes a single
    device string, not a device list. It also ignores ``reserve_gpus`` deliberately —
    the reserve exists so that inference has somewhere to run, so honouring it here
    would leave a single-GPU host unable to infer at all.

    A named device is honoured and only the batch is sized for it, which is the same rule
    :func:`resolve_devices` follows for training. With no policy to consult, or a card that
    cannot be described, there is nothing to size a batch against, so a batch that was not
    given falls back to the configured anchor rather than being guessed at.
    """
    if auto_gpu is not None and auto_gpu.enabled:
        if device is None:
            single = auto_gpu.model_copy(
                update={
                    "reserve_gpus": 0,
                    "min_devices": 1,
                    "max_gpus": 1,
                    # A run asking the queue for four cards to train on still infers on one.
                    "num_gpus": None if auto_gpu.num_gpus is None else 1,
                }
            )
            return select_devices(single, model=model, stage=stage, batch=batch)
        named = _card_behind(device) if batch is None else []
        if named:
            per_gpu = select_batch_per_gpu(auto_gpu, model, named, stage)
            logger.info("Inferring on GPU {} at batch {}", device, per_gpu)
            return DeviceSelection(
                devices=device, batch=per_gpu, batch_per_gpu=per_gpu, gpus=named
            )

    if batch is None:
        batch = DEFAULT_BATCH if auto_gpu is None else auto_gpu.batch_per_gpu
        logger.info("No GPU survey to size a batch against; inferring at batch {}", batch)
    return DeviceSelection(devices=device, batch=batch, batch_per_gpu=batch)


def resolve_devices(
    auto_gpu: AutoGpuConfig,
    device: list[int] | int | str | None,
    batch: int | None,
    model: str | None = None,
    stage: str = "train",
) -> DeviceSelection:
    """Pick the devices to train on and the batch to train at.

    Naming a device and naming a batch are separate decisions, the same way
    :func:`select_devices` already treats a batch that was asked for. A run that names its
    cards gets those cards — ``auto_gpu`` then only sizes the batch for them, which is
    what :func:`resolve_inference` has always done for the predict stage. Overriding a
    named device instead meant one word in the config file meant two different things
    depending on which stage read it.

    Only an unset device is surveyed for, and only an unset batch is derived. With
    ``auto_gpu`` off and no device named there is nothing to survey, so the run falls back
    to CPU as before.
    """
    if device is None:
        if auto_gpu.enabled:
            return select_devices(auto_gpu, model=model, stage=stage, batch=batch)
        logger.info("auto_gpu is disabled and no device was named; running on CPU")
        return _sized_by_anchor(auto_gpu, "cpu", batch)

    devices = _named_devices(device)
    named = _cards_behind(devices) if batch is None and auto_gpu.enabled else []
    if not named:
        return _sized_by_anchor(auto_gpu, devices, batch)

    per_gpu = select_batch_per_gpu(auto_gpu, model, named, stage)
    total = per_gpu * len(named)
    logger.info(
        "Training on the requested devices {} — {} x {} = total batch {}",
        devices,
        len(named),
        per_gpu,
        total,
    )
    return DeviceSelection(devices=devices, batch=total, batch_per_gpu=per_gpu, gpus=named)


def _sized_by_anchor(
    auto_gpu: AutoGpuConfig, devices: list[int] | str, batch: int | None
) -> DeviceSelection:
    """Run on ``devices`` at the batch given, or at the configured anchor per card.

    The fallback for every path with no card survey behind it: ``auto_gpu`` disabled, or a
    device named that NVML cannot describe. There is nothing to size against, so the
    anchor is used rather than a number guessed from hardware nobody looked at.
    """
    world_size = len(devices) if isinstance(devices, list) else 1
    if batch is None:
        batch = auto_gpu.batch_per_gpu * world_size
        logger.info("No survey to size a batch against; running at batch {}", batch)
    _refuse_indivisible_batch(batch, world_size, chosen_here=False)
    per_gpu = batch // world_size if batch > 0 else batch
    return DeviceSelection(devices=devices, batch=batch, batch_per_gpu=per_gpu)


def _write_remembered(path: Path, table: dict[str, Any]) -> None:
    """Replace the file in one step, because several runs share this machine."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        json.dump(table, handle, indent=2, sort_keys=True)
        written = Path(handle.name)
    written.replace(path)


# The remembered table is one file for the whole machine, and the read and the write around
# a batch are two steps: two stages finishing at the same moment each read the table before
# either wrote it, and whichever wrote second erased the other's number. Both go through the
# queue's own claim primitive here, so there is one O_EXCL create in this codebase and not
# two spellings of it.
BATCH_TABLE_LOCK_SUFFIX = ".lock"
# A read-modify-write of this file is milliseconds, so a lock this old is one whose owner
# died holding it. Both times are the local machine's, which is where the cache lives.
ABANDONED_LOCK_SECONDS = 60.0
LOCK_POLL_SECONDS = 0.1
LOCK_WAIT_SECONDS = 10.0


@contextmanager
def _exclusively(lock: Path) -> Iterator[bool]:
    """Hold the lock file for the block, yielding False when it could not be taken.

    Not taking it means skipping the write rather than forcing it: a forced write is
    exactly the lost update this exists to prevent, and a batch left unrecorded costs
    nothing beyond the next run having to find it again.
    """
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while not _create_exclusive(lock, str(os.getpid())):
        if _is_abandoned(lock):
            logger.warning("Removing {}, which no live run has released", lock)
            lock.unlink(missing_ok=True)
            continue
        if time.monotonic() >= deadline:
            yield False
            return
        time.sleep(LOCK_POLL_SECONDS)
    try:
        yield True
    finally:
        lock.unlink(missing_ok=True)


def _is_abandoned(lock: Path) -> bool:
    try:
        return time.time() - lock.stat().st_mtime > ABANDONED_LOCK_SECONDS
    except FileNotFoundError:
        return False


def _record_batch(
    remembered: dict[str, Any], stage: str, key: str, card: str, count: str, batch: int
) -> bool:
    """Put the batch in the table where it belongs, saying whether it was worth keeping."""
    by_count = remembered.setdefault(stage, {}).setdefault(key, {}).setdefault(card, {})
    if not isinstance(by_count, dict) or batch <= int(by_count.get(count, 0)):
        return False
    by_count[count] = batch
    return True


def remember_batch(
    config: AutoGpuConfig, stage: str, model: str | None, selection: DeviceSelection
) -> None:
    """Write down a batch that ran to completion, so it need not be found again.

    Only a run that finished is evidence, and of those only the largest is worth keeping:
    that a small batch fits says nothing about a larger one, while a large batch that
    finished proves every smaller one would have. A run whose cards were never surveyed
    cannot be recorded at all — there is no card to file the number under.

    The table is re-read inside the lock and not before it: what another run wrote while
    this one was training is part of what this number has to beat.
    """
    key = model_key(model)
    if not config.remember_batch or key is None or not selection.gpus:
        return
    if selection.batch_per_gpu < 1:
        logger.info("Batch {} is ultralytics' own to choose; not remembering it", selection.batch)
        return

    card = _normalised(min(selection.gpus, key=lambda gpu: gpu.total_vram_gb).name)
    count = str(selection.world_size)
    path = batch_table_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusively(path.with_name(path.name + BATCH_TABLE_LOCK_SUFFIX)) as alone:
            if not alone:
                logger.warning(
                    "Another run is rewriting the remembered batch table {}; leaving batch "
                    "{} for {} unrecorded rather than overwriting theirs",
                    path,
                    selection.batch_per_gpu,
                    key,
                )
                return
            remembered = _remembered_batches()
            if not _record_batch(remembered, stage, key, card, count, selection.batch_per_gpu):
                return
            _write_remembered(path, remembered)
    except OSError as error:
        logger.warning("Cannot write the remembered batch table {} ({})", path, error)
        return
    logger.info(
        "Remembered batch {} per GPU for {} on {} x {} in {}",
        selection.batch_per_gpu,
        key,
        count,
        card,
        path,
    )
