"""Validated portable detector export contracts without inference SDK imports."""

import math
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from clearml_yolo.core.models import CheckpointDescriptor

Shape = tuple[StrictInt, StrictInt, StrictInt, StrictInt]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Precision = Literal["fp32", "fp16"]
_RGB_CHANNELS = 3
_MAX_BATCH = 4
_STRIDE = 32


class OptimizationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum: Shape
    optimum: Shape
    maximum: Shape

    @model_validator(mode="after")
    def ordered(self) -> Self:
        shapes = (self.minimum, self.optimum, self.maximum)
        for low, preferred, high in zip(*shapes, strict=True):
            if not 0 < low <= preferred <= high:
                raise ValueError("Profile dimensions must be positive and ordered")
        if any(shape[1] != _RGB_CHANNELS for shape in shapes):
            raise ValueError("Detector profiles require three RGB channels")
        if self.maximum[0] > _MAX_BATCH:
            raise ValueError("Detector profiles support at most four images")
        if any(dimension % _STRIDE for shape in shapes for dimension in shape[2:]):
            raise ValueError("Profile canvas dimensions must be divisible by 32")
        return self

    def accepts(self, shape: tuple[int, int, int, int]) -> bool:
        return all(
            low <= value <= high
            for low, value, high in zip(self.minimum, shape, self.maximum, strict=True)
        )


DEFAULT_PROFILES = (
    OptimizationProfile(
        minimum=(1, 3, 608, 960), optimum=(2, 3, 608, 960), maximum=(4, 3, 736, 960)
    ),
    OptimizationProfile(
        minimum=(1, 3, 128, 1536), optimum=(2, 3, 256, 1920), maximum=(4, 3, 256, 1920)
    ),
)


class InferencePolicy(BaseModel):
    """ROI confidence, class NMS and maximum detections baked into the graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conf: Annotated[float, Field(ge=0, le=1)] = 0.001
    iou: Annotated[float, Field(gt=0, le=1)] = 0.7
    max_det: Annotated[int, Field(strict=True, gt=0)] = 300


class ExportMetadata(BaseModel):
    """The graph hash identifies the unchanged standard ONNX, before plugin lowering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    descriptor: CheckpointDescriptor
    inference: InferencePolicy = Field(default_factory=InferencePolicy)
    graph_sha256: Digest
    engine_sha256: Digest | None = None
    opset: Literal[17] = 17
    precision: Precision = "fp32"
    profiles: tuple[OptimizationProfile, ...] = DEFAULT_PROFILES
    runtime_versions: dict[str, str] = Field(default_factory=dict)
    plugins: tuple[str, ...] = ()
    input_names: tuple[Literal["images"], Literal["image_sizes"]] = ("images", "image_sizes")
    output_names: tuple[Literal["detections"], Literal["counts"]] = ("detections", "counts")
    label_offset: Literal[1] = 1
    normalization_stage: Literal["before_resize"] = "before_resize"
    interpolation: Literal["bilinear"] = "bilinear"
    antialias: Literal[False] = False
    padding: Literal["normalized_zero"] = "normalized_zero"

    @model_validator(mode="after")
    def supported_descriptor(self) -> Self:
        if self.descriptor.backend != "fasterrcnn":
            raise ValueError("Embedded RPN/ROI detector export requires a Faster R-CNN checkpoint")
        if not self.profiles:
            raise ValueError("Export metadata requires at least one optimization profile")
        preprocessing = self.descriptor.preprocessing
        if preprocessing.resize != "letterbox" or preprocessing.stride != _STRIDE:
            raise ValueError("Export requires native letterboxing with stride32 padding")
        if not all(math.isfinite(value) for value in (*preprocessing.mean, *preprocessing.std)):
            raise ValueError("Export normalization values must be finite")
        if any(value <= 0 for value in preprocessing.std):
            raise ValueError("Export normalization deviations must be positive")
        return self
