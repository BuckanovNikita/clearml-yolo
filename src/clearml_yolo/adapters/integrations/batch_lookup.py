"""Resolve training capacity from prepared dataset evidence and an explicit profile."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from clearml_yolo.application.batch_ports import BatchEstimateStore
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import (
    ResolvedRecommendation,
    SyntheticWorkload,
    TrainingProfile,
    select_recommendation,
)


class _ImageDensity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    split: Literal["train", "val", "test"]
    boxes: Annotated[int, Field(strict=True, ge=0)]


class _PreparedManifest(BaseModel):
    """Validate the maintained manifest subset needed for capacity bounds."""

    model_config = ConfigDict(extra="ignore")

    class_names: Annotated[
        dict[int, Annotated[str, Field(strict=True, min_length=1)]], Field(min_length=1)
    ]
    images: Annotated[tuple[_ImageDensity, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def class_identifiers(self) -> Self:
        if set(self.class_names) != set(range(len(self.class_names))):
            raise ValueError("Prepared class identifiers must be contiguous and zero-based")
        return self


def dataset_workload(prepared: PreparedDataset) -> SyntheticWorkload:
    manifest = _PreparedManifest.model_validate_json(prepared.manifest.read_bytes())
    relevant = [image for image in manifest.images if image.split in {"train", "val"}]
    if not relevant:
        raise ValueError("Prepared dataset has no training or validation images")
    # A background-only subset needs no target memory, and safely fits the smallest
    # positive synthetic workload supported by the estimator.
    return SyntheticWorkload(
        classes=len(manifest.class_names),
        objects_per_image=max(1, *(image.boxes for image in relevant)),
    )


def resolve_batch_estimate(
    profile: TrainingProfile, prepared: PreparedDataset, store: BatchEstimateStore
) -> ResolvedRecommendation:
    workload = dataset_workload(prepared)
    catalogue = store.read()
    try:
        return select_recommendation(catalogue.cases, profile, workload)
    except ValueError as error:
        size = profile.nominal_size[0]
        raise ValueError(
            "No compatible validated training batch estimate. Run "
            f"cy-batch-estimate --imgsz {size} --models {profile.model.selection} "
            f"--classes {workload.classes} --objects-per-image {workload.objects_per_image} "
            f"--gpu-counts {profile.world_size} using the assigned GPUs, "
            "or set an explicit training batch."
        ) from error
