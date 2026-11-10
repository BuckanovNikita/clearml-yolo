"""Pure selection of editable per-device training batches."""

import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from clearml_yolo.core.batch_estimation import GPUHardware, NonemptyString, PositiveInt, SearchStatus

_GIB = 1024**3
_LABEL = re.compile(r"(.+) \[([0-9]+(?:\.[0-9]+)?) GiB\]")


class BatchSizeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gpu_label: NonemptyString
    gpu_name: NonemptyString
    total_memory_bytes: PositiveInt
    image_size: PositiveInt
    model: NonemptyString
    per_gpu_batch: PositiveInt
    origin: Literal["manual", "measurement"] = "manual"
    forced: bool = False
    source_status: SearchStatus | None = None
    source_diagnostic: str = ""
    source_estimate_key: str | None = None


class BatchSizeFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gpu_name: NonemptyString
    total_memory_bytes: PositiveInt
    image_size: PositiveInt
    model: NonemptyString


class BatchSizeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry: BatchSizeEntry
    target_gpu: GPUHardware
    fallback: bool

    @property
    def per_gpu_batch(self) -> int:
        return self.entry.per_gpu_batch


class BatchSizeTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    digest: str
    entries: tuple[BatchSizeEntry, ...] = ()
    failures: tuple[BatchSizeFailure, ...] = ()

    def exact(self, gpu: GPUHardware, size: int, model: str) -> BatchSizeEntry | None:
        candidates = [
            entry
            for entry in self.entries
            if entry.image_size == size
            and entry.model == model
            and entry.gpu_name == gpu.name
            and entry.total_memory_bytes == gpu.total_memory_bytes
        ]
        return min(candidates, key=lambda entry: (entry.per_gpu_batch, entry.gpu_label), default=None)

    def resolve(self, gpu: GPUHardware, size: int, model: str) -> BatchSizeSelection:
        exact = self.exact(gpu, size, model)
        if exact is not None:
            return BatchSizeSelection(entry=exact, target_gpu=gpu, fallback=False)
        failed = BatchSizeFailure(
            gpu_name=gpu.name, total_memory_bytes=gpu.total_memory_bytes, image_size=size, model=model
        )
        if failed in self.failures:
            raise ValueError(
                f"Confirmed no_capacity for {model} at {size} on {gpu.name}; remeasure or add an exact entry"
            )
        candidates = [
            entry
            for entry in self.entries
            if entry.image_size == size and entry.model == model and entry.total_memory_bytes <= gpu.total_memory_bytes
        ]
        if not candidates:
            raise ValueError(f"No batch table entry for {model} at {size} on {gpu.name}")
        selected = min(candidates, key=lambda entry: (-entry.total_memory_bytes, entry.per_gpu_batch, entry.gpu_name))
        return BatchSizeSelection(entry=selected, target_gpu=gpu, fallback=True)


def gpu_label(gpu: GPUHardware) -> str:
    """Readable labels are display identifiers; exact bytes remain metadata."""
    capacity = format(Decimal(gpu.total_memory_bytes) / _GIB, ".3f").rstrip("0").rstrip(".")
    if capacity == "0":
        capacity = format(Decimal(gpu.total_memory_bytes) / _GIB, "f")
    return f"{gpu.name} [{capacity} GiB]"


def parse_gpu_label(label: str) -> tuple[str, int]:
    match = _LABEL.fullmatch(label)
    if match is None:
        raise ValueError(f"Invalid GPU label {label!r}; expected 'GPU name [24 GiB]'")
    capacity = Decimal(match[2]) * _GIB
    if int(capacity) <= 0:
        raise ValueError(f"GPU capacity must represent at least one byte: {label!r}")
    return match[1], int(capacity)
