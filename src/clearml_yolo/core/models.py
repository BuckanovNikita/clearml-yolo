"""Validated detector recipes and portable checkpoint metadata, without SDK imports."""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

BackendName = Literal["ultralytics", "deimv2", "rfdetr", "fasterrcnn"]
Device = str | StrictInt | list[StrictInt] | None
ImageSize = (
    Annotated[int, Field(strict=True, gt=0)]
    | tuple[Annotated[int, Field(strict=True, gt=0)], Annotated[int, Field(strict=True, gt=0)]]
)

PRESETS: dict[str, dict[str, int]] = {
    "ultralytics": {"default": 640},
    "deimv2": {"s": 640, "m": 640, "l": 640, "x": 640},
    "rfdetr": {"nano": 384, "small": 512, "medium": 576, "large": 704},
    "fasterrcnn": {
        "resnet50_fpn": 800,
        "resnet101_fpn": 800,
        "convnext_tiny": 800,
        "swin_tiny": 800,
        "dinov2_small": 800,
        "dinov3_small": 800,
    },
}


class TrainSettings(BaseModel):
    """Common controls translated explicitly by each native training adapter."""

    model_config = ConfigDict(extra="forbid")

    device: Device = None
    epochs: Annotated[int, Field(strict=True, gt=0)] = 100
    batch: Annotated[int, Field(strict=True, gt=0)] = 4
    imgsz: ImageSize = 640
    workers: Annotated[int, Field(strict=True, ge=0)] = 4
    lr: Annotated[float, Field(gt=0)] = 0.0001
    weight_decay: Annotated[float, Field(ge=0)] = 0.0001
    seed: StrictInt = 0
    pretrained: StrictBool = True
    weights: Path | None = None
    backbone_weights: Path | None = None
    amp: StrictBool = True
    grad_accum_steps: Annotated[int, Field(strict=True, gt=0)] = 1
    use_ema: StrictBool = True


class PredictSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: Device = None
    batch: Annotated[int, Field(strict=True, gt=0)] = 1
    imgsz: ImageSize | None = None
    conf: Annotated[float, Field(ge=0, le=1)] = 0.001
    iou: Annotated[float, Field(gt=0, le=1)] = 0.7
    max_det: Annotated[int, Field(strict=True, gt=0)] = 300
    half: StrictBool = False


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: BackendName = "ultralytics"
    preset: str = "default"
    source_dir: Path | None = None
    train: TrainSettings = Field(default_factory=TrainSettings)
    predict: PredictSettings = Field(default_factory=PredictSettings)

    @model_validator(mode="before")
    @classmethod
    def native_resolution(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        values = dict(value)
        backend, preset = values.get("backend", "ultralytics"), values.get("preset", "default")
        if backend not in PRESETS or preset not in PRESETS[backend]:
            raise ValueError(f"Unknown model preset: {backend}/{preset}")
        train = values.get("train", {})
        if isinstance(train, Mapping):
            values["train"] = {"imgsz": PRESETS[backend][preset], **train}
        return values

    @model_validator(mode="after")
    def compatible_recipe(self) -> Self:
        if self.backend == "rfdetr":
            for size in (self.train.imgsz, self.predict.imgsz):
                if size is not None and (not isinstance(size, int) or size % 32):
                    raise ValueError("RF-DETR resolution must be square and divisible by 32")
        if self.source_dir is not None and self.backend != "deimv2":
            raise ValueError("source_dir is only supported for DEIMv2")
        return self


def model_preset(selection: str) -> ModelConfig:
    if selection == "ultralytics":
        return ModelConfig()
    backend, separator, preset = selection.partition("/")
    if not separator:
        raise ValueError(f"Expected backend/preset, got {selection!r}")
    return ModelConfig.model_validate({"backend": backend, "preset": preset})


class Preprocessing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resize: Literal["stretch", "letterbox", "shortest_edge"]
    size: ImageSize
    mean: tuple[float, float, float] = (0.485, 0.456, 0.406)
    std: tuple[float, float, float] = (0.229, 0.224, 0.225)
    stride: Annotated[int, Field(strict=True, gt=0)] = 32
    color: Literal["RGB"] = "RGB"


class CheckpointMetadata(BaseModel):
    """Stored inside the checkpoint; excludes its own hash to avoid self-reference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    backend: BackendName
    preset: str
    class_names: tuple[str, ...]
    preprocessing: Preprocessing
    dependencies: dict[str, str] = Field(default_factory=dict)
    source_revision: str | None = None

    @field_validator("class_names")
    @classmethod
    def foreground_labels(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not name for name in values) or len(values) != len(set(values)):
            raise ValueError("Checkpoint foreground labels must be unique and nonempty")
        return values

    @model_validator(mode="after")
    def registered_recipe(self) -> Self:
        if self.preset not in PRESETS[self.backend]:
            raise ValueError(f"Unknown checkpoint preset: {self.backend}/{self.preset}")
        return self


class CheckpointDescriptor(CheckpointMetadata):
    checkpoint_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class BackendTrainResult(BaseModel):
    """Native adapters return evidence; the invocation owner publishes it."""

    weights: Path
    metadata: CheckpointMetadata
    effective_args: dict[str, Any]
    metrics: dict[str, float] = Field(default_factory=dict)
    artifacts: list[Path] = Field(default_factory=list)
