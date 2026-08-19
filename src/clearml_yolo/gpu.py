"""Automatic GPU selection, admission control and model-aware batch sizing.

GPUs are surveyed through NVML rather than torch because NVML needs no CUDA context:
``torch.cuda.mem_get_info`` allocates roughly half a gigabyte on every device it probes,
which would occupy the very memory the survey is trying to measure.

A run does not merely pick devices, it waits for them and then claims them: starting
training on a host whose cards are busy either crashes or evicts someone else's inference,
and a card that was merely *seen* free is one a peer may take in the minutes before the
memory is actually held. The wait loop holds the run at the door until enough cards are
free, and a lease file taken through :mod:`clearml_yolo.run_queue` is what closes the
window between the two. With the queue in front of the cards the wait also becomes a
queue: entries are read before the survey, only the head of the order may claim, and a run
that has taken its place in line waits for its turn however long that is. A named
``device`` is exempt from the survey and not from the leases: it claims exactly the cards
it names, and refuses the ones a peer's lease covers rather than starting on top of them.

How many cards a run takes is ``min_gpus`` at the bottom and ``max_gpus`` at the top. With
no ceiling named a run takes every free card, less what the runs already waiting in line
asked for — which is what lets a second run start beside a first instead of behind it.
``force`` is the way past all of it, leases included, and it can put two trainings on one
card.

The batch a run lands on comes from the first of three sources that can answer, and which
one did is always logged, because a number arrived at silently is a number nobody can
correct. In order: the batch the stage was given outright, the largest batch a previous run
of this stage was seen to *finish* at on this hardware (:func:`remember_batch`), and
failing both :data:`DEFAULT_BATCH`. Every one of them is a measurement or an explicit
instruction; nothing here estimates a batch from a card's VRAM, because the estimate was
always the rung that was wrong.
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from itertools import takewhile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, NoReturn

from loguru import logger
from pydantic import BaseModel, Field, model_validator

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
# What a stage falls back to when no run of it has ever finished on this hardware and
# nobody named a batch. Small enough to fit the cards this project is run on.
DEFAULT_BATCH = 16


class AutoGpuConfig(BaseModel):
    """Policy for picking devices and deriving a total batch size from them."""

    enabled: bool = True
    # The floor: this run does not start on fewer cards than this, however long it waits.
    min_gpus: int = Field(default=1, ge=1)
    # The ceiling. Unset means "every free card", which the queue then caps by what the
    # runs already waiting asked for — see :func:`_how_many_to_take`. Naming it is how two
    # runs split a machine deterministically: `auto_gpu.max_gpus=3` on each of them.
    max_gpus: int | None = Field(default=None, ge=1)
    # The batch **per GPU**; the total handed to ultralytics is this times the card count.
    # Unset means the largest batch a run of this stage was seen to finish at on this
    # model and this card, and failing that DEFAULT_BATCH.
    batch_size: int | None = Field(default=None, ge=1)
    # Start regardless: no queue, no wait, no thresholds, and other runs' leases taken
    # from under them. Two trainings can land on one card and both die of it, so this is
    # only ever a person's deliberate choice at the command line.
    force: bool = False
    # The three guards below are unset by default, which means not checked at all. Between
    # runs of this project the leases arbitrate; these exist for the memory no lease covers
    # — CVAT, a ClearML server, another user, a Windows host outside WSL.
    min_free_vram_gb: float | None = Field(default=None, ge=0)
    max_used_fraction: float | None = Field(default=None, ge=0, le=1)
    # Foreign compute processes tolerated per card. Processes belonging to this run are
    # never counted here, so a stage that follows training on the same device is not
    # locked out by training's own leftover context.
    max_compute_processes: int | None = Field(default=None, ge=0)
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

    @model_validator(mode="after")
    def _a_ceiling_below_the_floor_can_never_be_met(self) -> AutoGpuConfig:
        if self.max_gpus is not None and self.max_gpus < self.min_gpus:
            raise ValueError(
                f"auto_gpu.max_gpus={self.max_gpus} is below auto_gpu.min_gpus="
                f"{self.min_gpus}, so no number of cards would ever satisfy both."
            )
        return self


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
    """Whether a guard this run set says the card is somebody else's.

    Every guard is off unless named, so by default this answers yes for every card and the
    leases are the whole arbitration. That is deliberate: between runs of this project a
    lease is exact where a memory threshold is a guess, and the memory a threshold catches
    is the memory *no* lease covers — another user, or the Windows host outside WSL.
    """
    if config.max_compute_processes is not None and (
        gpu.foreign_process_count > config.max_compute_processes
    ):
        logger.info(
            "GPU {} ({}) is busy: {} foreign compute process(es), limit {}",
            gpu.torch_index,
            gpu.name,
            gpu.foreign_process_count,
            config.max_compute_processes,
        )
        return False
    if config.min_free_vram_gb is not None and (
        gpu.effective_free_vram_gb < config.min_free_vram_gb
    ):
        logger.info(
            "GPU {} ({}) is full: {:.1f} GiB free, need {:.1f}",
            gpu.torch_index,
            gpu.name,
            gpu.effective_free_vram_gb,
            config.min_free_vram_gb,
        )
        return False
    if config.max_used_fraction is not None and gpu.used_fraction > config.max_used_fraction:
        logger.info(
            "GPU {} ({}) is full: {:.1%} of VRAM already used, limit {:.1%}",
            gpu.torch_index,
            gpu.name,
            gpu.used_fraction,
            config.max_used_fraction,
        )
        return False
    return True


def _how_many_to_take(free: int, config: AutoGpuConfig, waiting_others: Sequence[Entry]) -> int:
    """How many of the free cards this run may take, given who else is already in line.

    A named ``max_gpus`` is the whole answer: the run asked for a number and gets it, which
    is how a machine is split deterministically. Without one the run is greedy, and greed
    is what made the first run on an eight-card machine swallow it and every run after it
    queue. So the cards the queue has already promised elsewhere come off the top — never
    below ``min_gpus``, because a run that cannot start is not a run that has yielded.
    """
    if config.max_gpus is not None:
        return min(free, config.max_gpus)
    promised = sum(entry.num_gpus for entry in waiting_others)
    if promised:
        logger.info(
            "Taking at most {} of {} free card(s): {} promised to the {} run(s) already "
            "waiting. Name auto_gpu.max_gpus to split the machine exactly.",
            max(config.min_gpus, free - promised),
            free,
            promised,
            len(waiting_others),
        )
    return max(config.min_gpus, free - promised)


def _requested_devices(config: AutoGpuConfig) -> int:
    """How many cards this run has to hold before it may start."""
    return config.min_gpus


def _selectable(
    survey: GpuSurvey,
    config: AutoGpuConfig,
    *,
    unavailable: frozenset[int] = frozenset(),
    waiting_others: Sequence[Entry] = (),
) -> list[GpuInfo]:
    """The cards this run may take: usable, not under a lease, and no more than its share.

    ``waiting_others`` is empty for every caller with no queue behind it, which makes the
    share "everything free" and is the behaviour an unqueued run has always had.
    """
    available = [
        gpu
        for gpu in survey.gpus
        if gpu.torch_index not in unavailable and _is_available(gpu, config)
    ]
    keep = _how_many_to_take(len(available), config, waiting_others)
    freest_first = sorted(available, key=lambda gpu: gpu.free_vram_gb, reverse=True)
    return sorted(freest_first[:keep], key=lambda gpu: gpu.torch_index)


def _no_device_message(config: AutoGpuConfig, total: int, waited: float | None) -> str:
    preamble = (
        f"Waited {waited:.0f}s and still found"
        if waited is not None
        else "Auto GPU mode found"
    )
    return (
        f"{preamble} fewer than {config.min_gpus} usable device(s) among {total} GPU(s): "
        f"every card is busy, is held by another run's lease, or fails a guard this run "
        f"set. Lower auto_gpu.min_gpus, relax auto_gpu.min_free_vram_gb, "
        "auto_gpu.max_used_fraction or auto_gpu.max_compute_processes, extend "
        "auto_gpu.wait_timeout_seconds, set an explicit device, or start regardless with "
        "--force-gpu."
    )


# Cards are held for as long as the process lives rather than for one stage: predict runs
# on the card training has just used, and a lease given back in between is a lease a peer
# takes. One stack per card rather than one per claim, so that the surplus can be handed
# back the moment training is over and inference is down to a single device — see
# :func:`release_gpus_except`. The heartbeat inside ``holding`` is what lets a peer recover
# a card when the process is killed before any of these close.
_HELD: dict[int, ExitStack] = {}


def _hold(queue: RunQueue, gpu_indices: Sequence[int]) -> None:
    for index in gpu_indices:
        card = ExitStack()
        card.enter_context(queue.holding([index]))
        _HELD[index] = card


def _release_every_card() -> None:
    for index in list(_HELD):
        _HELD.pop(index).close()


atexit.register(_release_every_card)


def release_gpus_except(keep: Sequence[int]) -> None:
    """Give back every card this run holds but the ones named, and say which.

    Training is the only stage that ever wants more than one card: inference, metrics and
    the report that follow it in the same process run on one. Holding the rest to the end
    of the pipeline is a card a neighbour cannot have for no reason at all — the reason
    the leases outlive a stage is only that predict follows train onto *its* card.

    Closing a card's stack stops that card's heartbeat and releases the lease, and
    ``release_lease`` already refuses to unlink a file that has stopped being this run's,
    so a card reclaimed from under this run is left alone rather than taken from its new
    holder.
    """
    kept = set(keep)
    given_back = sorted(index for index in _HELD if index not in kept)
    if not given_back:
        return
    for index in given_back:
        _HELD.pop(index).close()
    logger.info(
        "Released GPU(s) {} now that only {} is still in use; the rest of this run needs "
        "one card",
        given_back,
        sorted(kept & set(_HELD)) or "no card",
    )


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
    if config.force:
        return _seized(config, waiting_room, probe=probe)
    if waiting_room is None:
        return _wait_alone(config, probe=probe, sleep=sleep, monotonic=monotonic)
    return _wait_in_turn(config, waiting_room, probe=probe, sleep=sleep)


def _seized(
    config: AutoGpuConfig, queue: RunQueue | None, *, probe: Callable[[], GpuSurvey]
) -> list[GpuInfo]:
    """Take the freest cards this instant, over every guard and every other run's lease.

    ``--force-gpu`` is a person at a keyboard saying they know better than the queue, so
    nothing here waits and nothing refuses: not the VRAM guards, not the order, not a peer
    already training on the card. What it cannot do is make the card bigger — two trainings
    seized onto one GPU is two runs dying of the same out-of-memory — so every card taken
    from somebody is named in a warning, and so is the risk.
    """
    survey = _surveyed(probe)
    if survey is None:
        return []
    _refuse_more_cards_than_the_machine_has(config, survey)

    wanted = config.max_gpus if config.max_gpus is not None else config.min_gpus
    freest_first = sorted(survey.gpus, key=lambda gpu: gpu.free_vram_gb, reverse=True)
    cards = sorted(freest_first[:wanted], key=lambda gpu: gpu.torch_index)
    logger.warning(
        "--force-gpu: taking GPU(s) {} without queueing and without checking whether they "
        "are free. A card already training something will now run two trainings and both "
        "may die of it.",
        [gpu.torch_index for gpu in cards],
    )
    if queue is not None:
        _hold(queue, [lease.gpu_index for lease in queue.seize_leases(
            [gpu.torch_index for gpu in cards]
        )])
    return cards


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


def _surveyed(probe: Callable[[], GpuSurvey]) -> GpuSurvey | None:
    """One sweep of the hardware, or None when this run is to fall back to CPU."""
    survey = probe()
    if not survey.cuda_available:
        return None
    if survey.nvml_available:
        return survey
    raise RuntimeError(
        "NVML is unreachable, so GPU occupancy cannot be measured and this run would "
        "silently train on CPU — a hundredfold slowdown that looks exactly like success. "
        "Install nvidia-ml-py, or name a device explicitly to skip the survey."
    )


def _refuse_more_cards_than_the_machine_has(config: AutoGpuConfig, survey: GpuSurvey) -> None:
    """Reject a request no wait could satisfy, before this run takes a place in line.

    Selection can only ever yield cards the machine has, so a run asking for more of them
    than exist never leaves the wait. Queued, that is not merely its own hour lost: the
    queued wait reads no deadline and the entry is heartbeated every poll, so it stays at
    the head of the order for ever and every other run on the machine waits behind it.
    """
    needed = _requested_devices(config)
    if needed <= len(survey.gpus):
        return
    raise RuntimeError(
        f"auto_gpu.min_gpus={needed} asks for more GPU(s) than this machine has "
        f"({len(survey.gpus)}), so no wait can ever satisfy it and every run queued behind "
        f"this one would wait with it. Lower auto_gpu.min_gpus to at most "
        f"{len(survey.gpus)}, or run this where there are that many cards."
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
        survey = _surveyed(probe)
        if survey is None:
            return []
        _refuse_more_cards_than_the_machine_has(config, survey)

        needed = _requested_devices(config)
        selectable = _selectable(survey, config)
        if len(selectable) >= needed:
            return selectable

        elapsed = monotonic() - started
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


def _taking_more_than_it_asked_for(config: AutoGpuConfig, free: int) -> bool:
    """Whether this run is about to take cards it never named a number for.

    A run with no entry yet may claim outright whenever the queue is empty, so two runs
    started seconds apart never see each other: the first takes the machine and the second
    waits for it. A run in this state instead enqueues, sleeps one poll and decides on the
    pass after, by which time a neighbour that started inside the window is in the order and
    :func:`_how_many_to_take` can leave it its share.

    One poll is the whole cost, it is paid once, and only by a run taking more than it
    asked for. A run that named ``max_gpus`` is exact about its share already and goes
    straight through.
    """
    return config.max_gpus is None and free > config.min_gpus


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
    _hold(queue, [lease.gpu_index for lease in taken])
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
            survey = _surveyed(probe)
            if survey is None:
                return []
            _refuse_more_cards_than_the_machine_has(config, survey)

            mine = frozenset(
                lease.gpu_index for lease in leases if lease.run_id == queue.run_id
            )
            held = [gpu for gpu in survey.gpus if gpu.torch_index in mine]
            if len(held) >= needed:
                logger.info("Reusing GPU(s) this run already holds a lease on: {}", sorted(mine))
                return held[:needed]

            under_lease = frozenset(lease.gpu_index for lease in leases)
            others = [other for other in waiting if other.run_id != queue.run_id]
            free = _selectable(
                survey, config, unavailable=under_lease, waiting_others=others
            )
            settling = entry is None and _taking_more_than_it_asked_for(config, len(free))
            enough = len(held) + len(free) >= needed
            if enough and not settling and _at_the_head(entry, waiting, queue):
                cards = _claimed(queue, held, free)
                if cards:
                    return cards

            if entry is None:
                entry = queue.enqueue(needed)
                logger.info(
                    "Taking a place in the queue at {} as entry {} for {} GPU(s)",
                    queue.dir,
                    entry.seq,
                    needed,
                )
                if not settling:
                    continue
                logger.info(
                    "{} card(s) are free and this run named no auto_gpu.max_gpus; waiting "
                    "one poll before claiming, so that a run starting right now gets a share",
                    len(free),
                )
                sleep(queue.config.poll_seconds)
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
    """The per-GPU batch for this model on these cards, saying which source answered.

    The smallest card decides, because DDP splits the total evenly and the weakest device
    is the one that runs out of memory first.
    """
    if config.batch_size is not None:
        logger.info("Batch per GPU {} from auto_gpu.batch_size", config.batch_size)
        return config.batch_size

    smallest = min(gpus, key=lambda gpu: gpu.total_vram_gb)
    key = model_key(model)
    world_size = len(gpus)
    finished = table_batch(_remembered_batches().get(stage, {}), key, smallest.name, world_size)
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

    logger.info(
        "No {} run of {} has finished on {} x {} yet; starting from batch {} per GPU and "
        "remembering it if it works",
        stage,
        key,
        world_size,
        smallest.name,
        DEFAULT_BATCH,
    )
    return DEFAULT_BATCH


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
        if batch is None:
            batch = config.batch_size if config.batch_size is not None else DEFAULT_BATCH
        on_cpu = batch
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


def _named_devices(device: object) -> list[int] | str:
    """Spell a requested device the way ultralytics and torch both take it.

    ``"0"`` and ``"0,1"`` are how a device reaches this from a config file, ``0`` and
    ``[0, 1]`` are what hydra makes of the same words written unquoted on the command
    line, and a list is how ultralytics wants a multi-GPU run named — one request written
    four ways, which have to resolve to one thing. A string that is not a list of CUDA
    ordinals — ``"cpu"``, ``"mps"`` — is ultralytics' to interpret and passes through as
    it stands. Anything else names no card anybody here can find, and is refused by name
    rather than carried on until it surfaces as an attribute error from inside a string
    method, halfway through a run that has already taken leases.

    A sequence rather than a list, because the value arrives through hydra and an
    ``omegaconf`` container is a sequence that is not a ``list``.
    """
    parts = device.split(",") if isinstance(device, str) else device
    if isinstance(parts, int):
        parts = [parts]
    if isinstance(parts, Sequence) and not isinstance(parts, str | bytes):
        ordinals = [str(part).strip().removeprefix("cuda:") for part in parts]
        if ordinals and all(ordinal.isdigit() for ordinal in ordinals):
            return [int(ordinal) for ordinal in ordinals]
    if isinstance(device, str):
        return device
    raise RuntimeError(
        f"device={device!r} names nothing this run can resolve to a card. Name a CUDA "
        f'ordinal (0), a list of them ([0, 1]), either of those as a string ("0", "0,1", '
        f'"cuda:0"), or "cpu"; leave it unset to be given free cards in turn.'
    )


def _cards_behind(devices: list[int] | str) -> list[GpuInfo]:
    """Describe every card a requested device list names, without waiting for any.

    A stage that follows training in one process is handed training's own card rather
    than surveying for one, because this process still holds that card's memory and a
    survey would wait for a device the run already owns. The cards still have to be
    described — otherwise the whole batch policy stops at the one path the pipeline
    always takes, and a table written for this hardware would go unread there.
    """
    if not isinstance(devices, list):
        return []
    by_index = {gpu.torch_index: gpu for gpu in probe_gpus().gpus}
    found = [by_index[index] for index in devices if index in by_index]
    return found if len(found) == len(devices) else []


def _peer_leases_on(
    leases: Sequence[Lease], devices: Sequence[int], own_run_id: str
) -> list[Lease]:
    """The leases some run other than this one holds on the cards this run named."""
    named = set(devices)
    return [
        lease for lease in leases if lease.gpu_index in named and lease.run_id != own_run_id
    ]


def _refuse_the_named_cards(devices: Sequence[int], held: Sequence[Lease]) -> NoReturn:
    """Say which named card is not this run's to take, and how to get past it.

    Refusing rather than waiting, because a named device is a request for those cards and
    no others: there is no card the queue could offer instead, and nothing to queue behind
    but one particular run. ``held`` is empty when the claim was lost in the moment between
    reading the leases and taking them, so there is no holder to name yet.
    """
    holders = (
        ", ".join(
            f"GPU {lease.gpu_index} held by {lease.user}:{lease.run_id} (pid {lease.pid})"
            for lease in held
        )
        or "another run took them between reading the leases and claiming them"
    )
    raise RuntimeError(
        f"device={list(devices)} names GPU(s) this machine's queue says are taken: "
        f"{holders}. Leave the device unset to be given free cards in turn, wait for that "
        f"run to finish (`cy-queue` lists it), or set auto_gpu.queue.enabled=false to "
        f"share the card deliberately."
    )


def _lease_the_named_cards(config: AutoGpuConfig, devices: list[int] | str) -> None:
    """Hold a lease on every card this run named, or refuse because a peer holds one.

    A named device skips the availability survey deliberately — that is the escape hatch
    from the WSL blanket process count — but it used to skip the leases with it, and those
    are two different things. Without a lease a run named onto a card trains straight on
    top of the peer already training there, and writes nothing that would stop a queued run
    taking the same card during the minutes before its first CUDA allocation. What NVML
    says about the card is still nobody's business here: this arbitrates between our own
    runs and nothing more.

    Exactly the named indices are claimed, never a substitute and never re-ordered. Leases
    this process already holds are left as they are, because that is the pipeline's own
    later stage arriving on the card training chose, and re-claiming would refuse itself.
    """
    if not isinstance(devices, list):
        return
    queue = _queue_for(config)
    if queue is None:
        return
    leases = queue.live_leases()
    held_elsewhere = _peer_leases_on(leases, devices, queue.run_id)
    if held_elsewhere:
        _refuse_the_named_cards(devices, held_elsewhere)

    already_mine = {lease.gpu_index for lease in leases if lease.run_id == queue.run_id}
    wanted = [index for index in devices if index not in already_mine]
    if not wanted:
        logger.info("Reusing the lease(s) this run already holds on GPU(s) {}", devices)
        return
    taken = queue.claim_leases(wanted)
    if not taken:
        _refuse_the_named_cards(
            devices, _peer_leases_on(queue.live_leases(), wanted, queue.run_id)
        )
    _hold(queue, [lease.gpu_index for lease in taken])
    logger.info("Holding the named GPU(s) {} against the other runs on this machine", wanted)


def resolve_inference(
    auto_gpu: AutoGpuConfig | None,
    device: list[int] | int | str | None,
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

    A named card is leased before it is inferred on, the same way :func:`resolve_devices`
    leases one — inside the pipeline that card is training's own, and the lease this
    process already holds on it is recognised rather than claimed a second time. Which
    card was named is read through :func:`_named_devices` here as it is there, so that
    every spelling hydra can make of the same card means the same card in both, and one
    it cannot read is refused before any lease is taken rather than after.
    """
    named_device = None if device is None else _named_devices(device)
    if auto_gpu is not None and named_device is not None:
        _lease_the_named_cards(auto_gpu, named_device)
    if auto_gpu is not None and auto_gpu.enabled:
        if named_device is None:
            # A run asking the queue for four cards to train on still infers on one.
            single = auto_gpu.model_copy(update={"min_gpus": 1, "max_gpus": 1})
            return select_devices(single, model=model, stage=stage, batch=batch)
        cards = _cards_behind(named_device) if batch is None else []
        if cards:
            per_gpu = select_batch_per_gpu(auto_gpu, model, cards, stage)
            logger.info("Inferring on GPU {} at batch {}", named_device, per_gpu)
            return DeviceSelection(
                devices=named_device, batch=per_gpu, batch_per_gpu=per_gpu, gpus=cards
            )

    if batch is None:
        configured = None if auto_gpu is None else auto_gpu.batch_size
        batch = DEFAULT_BATCH if configured is None else configured
        logger.info("No GPU survey to size a batch against; inferring at batch {}", batch)
    return DeviceSelection(devices=named_device, batch=batch, batch_per_gpu=batch)


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
    depending on which stage read it. Getting those cards is not the same as taking them
    from a peer: the named indices are leased before anything runs on them, and a card a
    peer's live lease covers is refused rather than trained on top of.

    Only an unset device is surveyed for, and only an unset batch is derived. With
    ``auto_gpu`` off and no device named there is nothing to survey, so the run falls back
    to CPU as before.
    """
    if device is None:
        if auto_gpu.enabled:
            return select_devices(auto_gpu, model=model, stage=stage, batch=batch)
        logger.info("auto_gpu is disabled and no device was named; running on CPU")
        return _sized_without_a_survey(auto_gpu, "cpu", batch)

    devices = _named_devices(device)
    _lease_the_named_cards(auto_gpu, devices)
    named = _cards_behind(devices) if batch is None and auto_gpu.enabled else []
    if not named:
        return _sized_without_a_survey(auto_gpu, devices, batch)

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


def _sized_without_a_survey(
    auto_gpu: AutoGpuConfig, devices: list[int] | str, batch: int | None
) -> DeviceSelection:
    """Run on ``devices`` at the batch given, or at the configured one per card.

    The fallback for every path with no card survey behind it: ``auto_gpu`` disabled, or a
    device named that NVML cannot describe. There is no card to look a remembered batch up
    against, so ``batch_size`` answers and :data:`DEFAULT_BATCH` answers after it.
    """
    world_size = len(devices) if isinstance(devices, list) else 1
    if batch is None:
        per_card = auto_gpu.batch_size if auto_gpu.batch_size is not None else DEFAULT_BATCH
        batch = per_card * world_size
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


def remember_batch(stage: str, model: str | None, selection: DeviceSelection) -> None:
    """Write down a batch that ran to completion, so it need not be found again.

    Only a run that finished is evidence, and of those only the largest is worth keeping:
    that a small batch fits says nothing about a larger one, while a large batch that
    finished proves every smaller one would have. A run whose cards were never surveyed
    cannot be recorded at all — there is no card to file the number under.

    The table is re-read inside the lock and not before it: what another run wrote while
    this one was training is part of what this number has to beat.
    """
    key = model_key(model)
    if key is None or not selection.gpus:
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
