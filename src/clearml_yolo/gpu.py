"""Automatic GPU selection and VRAM-aware batch sizing.

GPUs are surveyed through NVML rather than torch because NVML needs no CUDA context:
``torch.cuda.mem_get_info`` allocates roughly half a gigabyte on every device it probes,
which would occupy the very memory the survey is trying to measure.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

BYTES_PER_GIB = 1 << 30


class AutoGpuConfig(BaseModel):
    """Policy for picking devices and deriving a total batch size from them."""

    enabled: bool = True
    batch_per_gpu: int = Field(default=16, ge=1)
    reference_vram_gb: float = Field(default=24.0, gt=0)
    min_free_vram_gb: float = Field(default=8.0, ge=0)
    # Workstations with an attached display idle around 10% VRAM before any training
    # starts, so a stricter threshold would reject every local GPU.
    max_used_fraction: float = Field(default=0.25, ge=0, le=1)
    max_gpus: int | None = None
    scale_to_vram: bool = True
    round_to_power_of_two: bool = True


class GpuInfo(BaseModel):
    """A physical GPU as seen by NVML, already matched to its torch index."""

    torch_index: int
    name: str
    uuid: str
    total_vram_gb: float
    free_vram_gb: float
    compute_process_count: int

    @property
    def used_fraction(self) -> float:
        return 1.0 - self.free_vram_gb / self.total_vram_gb


class DeviceSelection(BaseModel):
    """What the training run should be handed: devices plus a divisible batch."""

    devices: list[int] | str
    batch: int
    batch_per_gpu: int
    gpus: list[GpuInfo] = Field(default_factory=list)

    @property
    def world_size(self) -> int:
        return len(self.devices) if isinstance(self.devices, list) else 1


def _decode(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _nvml_handles_by_uuid(pynvml: Any) -> dict[str, Any]:
    handles: dict[str, Any] = {}
    for index in range(pynvml.nvmlDeviceGetCount()):
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)
        handles[_decode(pynvml.nvmlDeviceGetUUID(handle))] = handle
    return handles


def probe_gpus() -> list[GpuInfo]:
    """Describe every GPU torch can see, reading live memory figures from NVML.

    Devices are matched by UUID because NVML ignores ``CUDA_VISIBLE_DEVICES`` while
    torch honours it, so identical indices routinely denote different cards.
    """
    import torch

    if not torch.cuda.is_available():
        logger.warning("CUDA is unavailable; no GPUs to probe")
        return []

    try:
        import pynvml
    except ImportError:
        logger.warning("nvidia-ml-py is not installed; cannot inspect GPU memory")
        return []

    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError as error:
        logger.warning("NVML initialisation failed ({}); cannot inspect GPU memory", error)
        return []

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
            gpus.append(
                GpuInfo(
                    torch_index=torch_index,
                    name=properties.name,
                    uuid=bare_uuid,
                    total_vram_gb=memory.total / BYTES_PER_GIB,
                    free_vram_gb=memory.free / BYTES_PER_GIB,
                    compute_process_count=len(pynvml.nvmlDeviceGetComputeRunningProcesses(handle)),
                )
            )
        return gpus
    finally:
        pynvml.nvmlShutdown()


def _is_available(gpu: GpuInfo, config: AutoGpuConfig) -> bool:
    if gpu.compute_process_count > 0:
        logger.info(
            "Skipping GPU {} ({}): {} compute process(es) already running",
            gpu.torch_index,
            gpu.name,
            gpu.compute_process_count,
        )
        return False
    if gpu.free_vram_gb < config.min_free_vram_gb:
        logger.info(
            "Skipping GPU {} ({}): {:.1f} GiB free, need {:.1f}",
            gpu.torch_index,
            gpu.name,
            gpu.free_vram_gb,
            config.min_free_vram_gb,
        )
        return False
    if gpu.used_fraction > config.max_used_fraction:
        logger.info(
            "Skipping GPU {} ({}): {:.1%} of VRAM already used, limit {:.1%}",
            gpu.torch_index,
            gpu.name,
            gpu.used_fraction,
            config.max_used_fraction,
        )
        return False
    return True


def _floor_power_of_two(value: int) -> int:
    return 1 << (value.bit_length() - 1) if value > 0 else 1


def scale_batch_per_gpu(config: AutoGpuConfig, gpus: list[GpuInfo]) -> int:
    """Fit the configured per-GPU batch to the smallest selected card.

    DDP splits the total batch evenly, so the weakest device sets the ceiling for
    every device.
    """
    if not config.scale_to_vram or not gpus:
        return config.batch_per_gpu

    smallest_vram = min(gpu.total_vram_gb for gpu in gpus)
    scaled = int(config.batch_per_gpu * smallest_vram / config.reference_vram_gb)
    if config.round_to_power_of_two:
        scaled = _floor_power_of_two(scaled)
    scaled = max(1, scaled)
    if scaled != config.batch_per_gpu:
        logger.info(
            "Scaled batch per GPU {} -> {} ({:.1f} GiB smallest card vs {:.1f} GiB reference)",
            config.batch_per_gpu,
            scaled,
            smallest_vram,
            config.reference_vram_gb,
        )
    return scaled


def select_devices(config: AutoGpuConfig) -> DeviceSelection:
    """Choose the devices to train on and the total batch size to pass to YOLO.

    The returned batch is always a multiple of the device count: ultralytics treats
    ``batch`` as the total across ranks and floor-divides it by world size without
    checking divisibility, silently shrinking the effective batch otherwise.
    """
    gpus = probe_gpus()
    if not gpus:
        logger.warning("Falling back to CPU with batch {}", config.batch_per_gpu)
        return DeviceSelection(
            devices="cpu", batch=config.batch_per_gpu, batch_per_gpu=config.batch_per_gpu
        )

    available = [gpu for gpu in gpus if _is_available(gpu, config)]
    if not available:
        raise RuntimeError(
            f"Auto GPU mode found no free device among {len(gpus)}: every GPU is busy or "
            f"has less than {config.min_free_vram_gb} GiB free. Lower auto_gpu."
            "min_free_vram_gb, raise auto_gpu.max_used_fraction, or set an explicit device."
        )

    if config.max_gpus is not None:
        available = sorted(available, key=lambda gpu: gpu.free_vram_gb, reverse=True)
        available = sorted(available[: config.max_gpus], key=lambda gpu: gpu.torch_index)

    batch_per_gpu = scale_batch_per_gpu(config, available)
    devices = [gpu.torch_index for gpu in available]
    selection = DeviceSelection(
        devices=devices,
        batch=batch_per_gpu * len(devices),
        batch_per_gpu=batch_per_gpu,
        gpus=available,
    )
    logger.info(
        "Auto GPU selected devices {} — {} x {} = total batch {}",
        devices,
        len(devices),
        batch_per_gpu,
        selection.batch,
    )
    return selection


def resolve_devices(
    auto_gpu: AutoGpuConfig, device: list[int] | int | str | None, batch: int
) -> DeviceSelection:
    """Pick devices automatically or validate an explicitly requested configuration."""
    if auto_gpu.enabled:
        if device is not None:
            logger.warning("auto_gpu is enabled; ignoring explicit device={}", device)
        return select_devices(auto_gpu)

    devices: list[int] | str
    if device is None:
        devices = "cpu"
    elif isinstance(device, int):
        devices = [device]
    else:
        devices = device

    world_size = len(devices) if isinstance(devices, list) else 1
    if batch < 1 and world_size > 1:
        raise ValueError(
            f"batch={batch} requests ultralytics AutoBatch, which is single-GPU only, but "
            f"{world_size} devices were given. Set an explicit batch that is a multiple of "
            f"{world_size}, or enable auto_gpu."
        )
    if world_size > 1 and batch % world_size:
        raise ValueError(
            f"batch={batch} is not divisible by {world_size} devices; ultralytics would "
            f"silently train on {batch // world_size * world_size} images per step."
        )

    per_gpu = batch // world_size if batch > 0 else batch
    return DeviceSelection(devices=devices, batch=batch, batch_per_gpu=per_gpu)
