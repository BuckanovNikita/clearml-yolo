"""Resolve training batches exclusively from the editable capacity table."""

from typing import Annotated

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.core.batch_estimation import GPUHardware, ModelVariant
from clearml_yolo.core.batch_sizes import BatchSizeSelection


class TableRecommendation(BaseModel):
    """Table choices retain their sources without asserting target measurements."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table_digest: str
    model: str
    image_size: int
    selections: Annotated[tuple[BatchSizeSelection, ...], Field(min_length=1)]

    @property
    def per_gpu_batch(self) -> int:
        return min(selection.per_gpu_batch for selection in self.selections)

    @property
    def global_batch(self) -> int:
        return len(self.selections) * self.per_gpu_batch


def resolve_batch_estimate(
    model: ModelVariant,
    imgsz: int,
    gpus: tuple[GPUHardware, ...],
    store: BatchSizeStore,
    *,
    device_indices: tuple[int, ...] | None = None,
) -> TableRecommendation:
    table = store.load()
    command = f"cy-batch-estimate --imgsz {imgsz} --models {model.selection}"
    try:
        selections = tuple(table.resolve(gpu, imgsz, model.selection) for gpu in gpus)
    except ValueError as error:
        raise ValueError(
            f"No training batch table entry: {error}. Run {command} using the assigned GPUs, "
            "or set an explicit training batch."
        ) from error
    recommendation = TableRecommendation(
        table_digest=table.digest,
        model=model.selection,
        image_size=imgsz,
        selections=selections,
    )
    for index, selection in enumerate(selections):
        if selection.entry.forced:
            logger.warning(
                "Training batch source {} is forced/background-sensitive; "
                "its capacity reflects the recorded background activity, not an uncontended maximum.",
                selection.entry.gpu_label,
            )
        if selection.fallback:
            target_command = command
            if device_indices is not None:
                target_command += f" --devices {device_indices[index]} --gpu-counts 1"
            logger.warning(
                "Training batch fallback for {} uses {}: per-GPU batch {}. "
                "This is a table value from another GPU, not a measurement on the target. "
                "Run {} on the current GPU to estimate its capacity.",
                selection.target_gpu.name,
                selection.entry.gpu_label,
                selection.per_gpu_batch,
                target_command,
            )
    return recommendation
