"""Explicit native rank setup for already selected devices; never schedules GPUs."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from clearml_yolo.core.models import Device


def selected_gpu_indices(value: Device) -> tuple[int, ...]:
    """Parse explicit CUDA selections; empty means native single-device/default policy."""
    if value is None or value in ("cpu", "cuda", "mps", -1, "-1") or value == [-1]:
        return ()
    if isinstance(value, int):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = [int(item.removeprefix("cuda:")) for item in value.split(",")]
    if not values or any(index < 0 for index in values) or len(set(values)) != len(values):
        raise ValueError("Native training devices must be distinct nonnegative GPU indices")
    return tuple(values)


def global_batch_per_rank(batch: int | None, world_size: int) -> int:
    if batch is None:
        raise ValueError("Resolve batch=null with cy-batch-estimate before native training")
    if batch < 1 or world_size < 1 or batch % world_size:
        raise ValueError("Global training batch must be positive and divisible by GPU count")
    return batch // world_size


@contextmanager
def native_rank(*, initialize: bool) -> Iterator[None]:
    """Set CUDA device before model construction; Lightning owns its own group setup."""
    import torch
    import torch.distributed as dist

    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    torch.cuda.set_device(local_rank)
    try:
        if initialize and world_size > 1:
            dist.init_process_group(backend="nccl", timeout=timedelta(seconds=120))
            if dist.get_world_size() != world_size:
                raise RuntimeError("Native process group world size disagrees with request")
        yield
    finally:
        if dist.is_initialized():
            # No barrier: a failed peer cannot be required to participate in cleanup.
            dist.destroy_process_group()
