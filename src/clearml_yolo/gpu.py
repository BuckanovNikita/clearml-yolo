"""Automatic GPU selection, admission control and model-aware batch sizing.

GPUs are surveyed through NVML rather than torch because NVML needs no CUDA context:
``torch.cuda.mem_get_info`` allocates roughly half a gigabyte on every device it probes,
which would occupy the very memory the survey is trying to measure.

A run does not merely pick devices, it waits for them: starting training on a host whose
cards are busy either crashes or evicts someone else's inference. Two policies express
that. ``reserve_gpus`` leaves cards behind for other runs to infer on, and the wait loop
holds the run at the door until enough cards are free.

The batch a run lands on comes from the first of five sources that can answer, and which
one did is always logged, because a number arrived at silently is a number nobody can
correct. In order: the batch the stage was given outright, the ``batch_table`` this
hardware was measured into, the batch a previous run of this stage was seen to finish at
(:func:`remember_batch`), a per-model anchor scaled by the card's VRAM, and finally the
one global anchor scaled the same way. The first three are measurements and are used as
they stand; the last two are a batch at a reference card, so both go through the ratio.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator

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
    wait_timeout_seconds: float = Field(default=3600.0, gt=0)
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


def _belongs_to_this_run(pid: int, own_group: int | None) -> bool:
    """Whether a compute process is this process or one of its DDP children."""
    if pid == os.getpid():
        return True
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
    """
    if not WSL_GPU_DEVICE.exists():
        return None
    foreign = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if not _belongs_to_this_run(pid, own_group) and _holds_the_wsl_gpu_device(pid):
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


def _selectable(survey: GpuSurvey, config: AutoGpuConfig) -> list[GpuInfo]:
    return _apply_reserve([gpu for gpu in survey.gpus if _is_available(gpu, config)], config)


def _no_device_message(config: AutoGpuConfig, total: int, waited: float | None) -> str:
    preamble = (
        f"Waited {waited:.0f}s and still found"
        if waited is not None
        else "Auto GPU mode found"
    )
    return (
        f"{preamble} fewer than {config.min_devices} usable device(s) among {total} GPU(s): "
        f"every card is busy, holds less than {config.min_free_vram_gb} GiB free, or is "
        f"held back by reserve_gpus={config.reserve_gpus}. Lower auto_gpu.min_free_vram_gb, "
        "raise auto_gpu.max_used_fraction or auto_gpu.max_compute_processes, drop "
        "auto_gpu.reserve_gpus, extend auto_gpu.wait_timeout_seconds, or set an explicit device."
    )


def wait_for_devices(
    config: AutoGpuConfig,
    *,
    probe: Callable[[], GpuSurvey] = probe_gpus,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[GpuInfo]:
    """Block until ``min_devices`` cards are free, then return the ones to use.

    An empty list means the host has no usable GPU at all and the caller should run on
    CPU. Every other outcome raises: a wait must never end by quietly downgrading the
    run to CPU, which is a hundredfold slowdown that looks exactly like success.

    ``probe``, ``sleep`` and ``monotonic`` are injected so the whole policy is testable
    without a GPU and without real time passing.
    """
    started = monotonic()
    while True:
        survey = probe()
        if not survey.cuda_available:
            return []
        if not survey.nvml_available:
            if config.cpu_fallback_on_nvml_failure:
                logger.warning("NVML is unreachable; falling back to CPU as configured")
                return []
            raise RuntimeError(
                "NVML is unreachable, so GPU occupancy cannot be measured and this run "
                "would silently train on CPU. Install nvidia-ml-py, or set "
                "auto_gpu.cpu_fallback_on_nvml_failure=true to accept that."
            )

        selectable = _selectable(survey, config)
        if len(selectable) >= config.min_devices:
            return selectable

        elapsed = monotonic() - started
        if not config.wait_for_free:
            raise RuntimeError(_no_device_message(config, len(survey.gpus), waited=None))
        remaining = config.wait_timeout_seconds - elapsed
        if remaining <= 0:
            raise RuntimeError(_no_device_message(config, len(survey.gpus), waited=elapsed))

        logger.info(
            "Waiting for {} free GPU(s): {} of {} usable, {:.0f}s elapsed, {:.0f}s before timeout",
            config.min_devices,
            len(selectable),
            len(survey.gpus),
            elapsed,
            remaining,
        )
        sleep(min(config.wait_poll_seconds, remaining))


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

    With no policy to consult, or a card that cannot be described, there is nothing to
    size a batch against, so a batch that was not given falls back to the configured
    anchor rather than being guessed at.
    """
    if auto_gpu is not None and auto_gpu.enabled:
        if device is None:
            single = auto_gpu.model_copy(
                update={"reserve_gpus": 0, "min_devices": 1, "max_gpus": 1}
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
    """Pick devices automatically or validate an explicitly requested configuration."""
    if auto_gpu.enabled:
        if device is not None:
            logger.warning("auto_gpu is enabled; ignoring explicit device={}", device)
        return select_devices(auto_gpu, model=model, stage=stage, batch=batch)

    devices: list[int] | str
    if device is None:
        devices = "cpu"
    elif isinstance(device, int):
        devices = [device]
    else:
        devices = device

    world_size = len(devices) if isinstance(devices, list) else 1
    if batch is None:
        batch = auto_gpu.batch_per_gpu * world_size
        logger.info("auto_gpu is disabled and no batch was given; running at batch {}", batch)
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


def remember_batch(
    config: AutoGpuConfig, stage: str, model: str | None, selection: DeviceSelection
) -> None:
    """Write down a batch that ran to completion, so it need not be found again.

    Only a run that finished is evidence, and of those only the largest is worth keeping:
    that a small batch fits says nothing about a larger one, while a large batch that
    finished proves every smaller one would have. A run whose cards were never surveyed
    cannot be recorded at all — there is no card to file the number under.
    """
    key = model_key(model)
    if not config.remember_batch or key is None or not selection.gpus:
        return
    if selection.batch_per_gpu < 1:
        logger.info("Batch {} is ultralytics' own to choose; not remembering it", selection.batch)
        return

    card = _normalised(min(selection.gpus, key=lambda gpu: gpu.total_vram_gb).name)
    count = str(selection.world_size)
    remembered = _remembered_batches()
    by_count = remembered.setdefault(stage, {}).setdefault(key, {}).setdefault(card, {})
    if not isinstance(by_count, dict) or selection.batch_per_gpu <= int(by_count.get(count, 0)):
        return

    by_count[count] = selection.batch_per_gpu
    path = batch_table_path()
    try:
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
