"""External-rank execution, equal training batches and unique validation partitions."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, override

import torch
from torch import distributed
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import Sampler

from clearml_yolo.core.models import Device


def execution_device(value: Device) -> torch.device:
    """Resolve one inference device; training groups use their local-rank device."""
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("Torchvision prediction requires one device")
        value = value[0]
    if value in (None, -1, "-1"):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if isinstance(value, int) or value.isdecimal():
        return torch.device(f"cuda:{value}")
    return torch.device(value)


@dataclass(frozen=True)
class TrainingContext:
    rank: int
    world_size: int
    device: torch.device
    per_rank_batch: int


def training_context(value: Device, global_batch: int | None) -> TrainingContext:
    initialized = distributed.is_available() and distributed.is_initialized()
    world_size = distributed.get_world_size() if initialized else 1
    rank = distributed.get_rank() if initialized else 0
    if global_batch is None:
        raise ValueError("Resolve batch=null against a saved estimate before native training")
    if global_batch < world_size or global_batch % world_size:
        raise ValueError("Training global batch must be positive and divisible by world size")
    multiple = (isinstance(value, list) and len(value) != 1) or (
        isinstance(value, str) and "," in value
    )
    if multiple and world_size == 1:
        raise ValueError("multi-device training requires a supervised initialized process group")
    if world_size > 1 and value != "cpu":
        local_rank = int(os.environ["LOCAL_RANK"])
        torch.cuda.set_device(local_rank)
        device = torch.device("cuda", local_rank)
    else:
        device = execution_device(value)
    return TrainingContext(rank, world_size, device, global_batch // world_size)


def wrap_model(model: Any, context: TrainingContext) -> Any:
    if context.world_size == 1:
        return model
    indexes = [context.device.index] if context.device.type == "cuda" else None
    # Patch-token feature extraction leaves the pretrained classification head
    # unused; empty-target batches can also leave detector parameters unused.
    return DistributedDataParallel(model, device_ids=indexes, find_unused_parameters=True)


def unwrap_model(model: Any) -> Any:
    return model.module if isinstance(model, DistributedDataParallel) else model


def synchronize_buffers(model: Any) -> None:
    """Rank-zero running statistics also seed every rank's EMA buffers identically."""
    if distributed.is_available() and distributed.is_initialized():
        for buffer in unwrap_model(model).buffers():
            distributed.broadcast(buffer, src=0)


class DistributedEvaluationSampler(Sampler[int]):
    """Partition every validation image once, without padded duplicate samples."""

    def __init__(self, size: int, rank: int, world_size: int) -> None:
        if size < 0 or world_size < 1 or not 0 <= rank < world_size:
            raise ValueError("Invalid distributed validation partition")
        self.indices = range(rank, size, world_size)

    @override
    def __iter__(self) -> Iterator[int]:
        return iter(self.indices)

    def __len__(self) -> int:
        return len(self.indices)
