"""Validated detector recipes and portable checkpoint metadata, without SDK imports."""

# ruff: noqa: RUF001 -- Public configuration documentation is intentionally Russian.

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

BackendName = Literal["ultralytics", "deimv2", "rfdetr", "fasterrcnn", "fcos"]
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
    "fcos": {
        "resnet50_fpn": 800,
        "resnet101_fpn": 800,
        "convnext_tiny": 800,
        "swin_tiny": 800,
        "dinov2_small": 800,
        "dinov3_small": 800,
    },
}


class DeimAugmentationOverrides(BaseModel):
    """Visible native controls replaced by the shared training pipeline."""

    model_config = ConfigDict(extra="forbid")

    mosaic_prob: Annotated[float, Field(ge=0, le=1)] = Field(
        description=(
            "Вероятность нативного Mosaic DEIMv2 от 0 до 1; общий Albumentations-профиль задаёт 0."
        ),
        examples=[0.0],
        json_schema_extra={
            "shapes": "Annotated[float, Field(ge=0, le=1)]",
            "applicability": "DeimAugmentationOverrides",
            "source": "clearml_yolo.core.models.DeimAugmentationOverrides.mosaic_prob",
            "classification": "input",
        },
    )
    mixup_prob: Annotated[float, Field(ge=0, le=1)] = Field(
        description="Вероятность нативного MixUp DEIMv2 от 0 до 1; общий профиль задаёт 0.",
        examples=[0.0],
        json_schema_extra={
            "shapes": "Annotated[float, Field(ge=0, le=1)]",
            "applicability": "DeimAugmentationOverrides",
            "source": "clearml_yolo.core.models.DeimAugmentationOverrides.mixup_prob",
            "classification": "input",
        },
    )
    copyblend_prob: Annotated[float, Field(ge=0, le=1)] = Field(
        description="Вероятность нативного CopyBlend DEIMv2 от 0 до 1; общий профиль задаёт 0.",
        examples=[0.0],
        json_schema_extra={
            "shapes": "Annotated[float, Field(ge=0, le=1)]",
            "applicability": "DeimAugmentationOverrides",
            "source": "clearml_yolo.core.models.DeimAugmentationOverrides.copyblend_prob",
            "classification": "input",
        },
    )
    base_size_repeat: StrictInt | None = Field(
        description="Нативный повтор выбора базового размера DEIMv2; общий профиль задаёт null.",
        examples=[None],
        json_schema_extra={
            "shapes": "StrictInt | None",
            "applicability": "DeimAugmentationOverrides",
            "source": "clearml_yolo.core.models.DeimAugmentationOverrides.base_size_repeat",
            "classification": "input",
        },
    )
    ops: list[dict[str, JsonValue]] = Field(
        description="Список нативных операций DEIMv2; при общем pipeline остаётся пустым.",
        examples=[[]],
        json_schema_extra={
            "shapes": "list[dict[str, JsonValue]]",
            "applicability": "DeimAugmentationOverrides",
            "source": "clearml_yolo.core.models.DeimAugmentationOverrides.ops",
            "classification": "input",
        },
    )


class RFDETRAugmentationOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aug_config: dict[str, JsonValue] = Field(
        description=(
            "Карта нативной аугментации RF-DETR; общий pipeline отключает её пустой картой."
        ),
        examples=[{}],
        json_schema_extra={
            "shapes": "dict[str, JsonValue]",
            "applicability": "RFDETRAugmentationOverrides",
            "source": "clearml_yolo.core.models.RFDETRAugmentationOverrides.aug_config",
            "classification": "input",
        },
    )
    augmentation_backend: str = Field(
        description="Нативный backend RF-DETR; общий профиль использует torchvision.",
        examples=["torchvision"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "RFDETRAugmentationOverrides",
            "source": "clearml_yolo.core.models.RFDETRAugmentationOverrides.augmentation_backend",
            "classification": "input",
        },
    )
    scale_jitter: StrictBool = Field(
        description="Нативное случайное изменение масштаба RF-DETR; общий pipeline задаёт false.",
        examples=[False],
        json_schema_extra={
            "shapes": "StrictBool",
            "applicability": "RFDETRAugmentationOverrides",
            "source": "clearml_yolo.core.models.RFDETRAugmentationOverrides.scale_jitter",
            "classification": "input",
        },
    )
    multi_scale: str = Field(
        description="Нативный режим нескольких разрешений RF-DETR; общий pipeline задаёт off.",
        examples=["off"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "RFDETRAugmentationOverrides",
            "source": "clearml_yolo.core.models.RFDETRAugmentationOverrides.multi_scale",
            "classification": "input",
        },
    )


class EmptyAugmentationOverrides(BaseModel):
    """Faster R-CNN has no optional native dataset augmentation to disable."""

    model_config = ConfigDict(extra="forbid")


class TrainSettings(BaseModel):
    """Common controls translated explicitly by each native training adapter."""

    model_config = ConfigDict(extra="forbid")

    device: Device = Field(
        default=None,
        description=(
            "Нативный выбор устройств: cpu, строка CUDA, один индекс или список "
            "видимых индексов. null сохраняет выбор адаптера."
        ),
        examples=["cpu"],
        json_schema_extra={
            "shapes": "Device",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.device",
            "classification": "input",
        },
    )
    epochs: Annotated[int, Field(strict=True, gt=0)] = Field(
        default=100,
        description="Положительное целое число эпох обучения.",
        examples=[10],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)]",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.epochs",
            "classification": "input",
        },
    )
    batch: Annotated[int, Field(strict=True, gt=0)] | None = Field(
        default=4,
        description=(
            "Глобальный положительный размер пакета; null запрашивает подбор из "
            "совместимых измерений cy-batch-estimate."
        ),
        examples=[4],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)] | None",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.batch",
            "classification": "input",
        },
    )
    imgsz: ImageSize = Field(
        default=640,
        description=(
            "Номинальное разрешение: положительное целое либо пара высота/ширина."
            " RF-DETR требует квадрат и кратность 32."
        ),
        examples=[640],
        json_schema_extra={
            "shapes": "ImageSize",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.imgsz",
            "classification": "input",
        },
    )
    workers: Annotated[int, Field(strict=True, ge=0)] = Field(
        default=4,
        description="Число процессов загрузки данных; ноль выполняет загрузку в основном процессе.",
        examples=[4],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, ge=0)]",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.workers",
            "classification": "input",
        },
    )
    lr: Annotated[float, Field(gt=0)] = Field(
        default=0.0001,
        description="Положительная начальная скорость обучения нативного оптимизатора.",
        examples=[0.0001],
        json_schema_extra={
            "shapes": "Annotated[float, Field(gt=0)]",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.lr",
            "classification": "input",
        },
    )
    weight_decay: Annotated[float, Field(ge=0)] = Field(
        default=0.0001,
        description="Неотрицательный коэффициент регуляризации весов.",
        examples=[0.0001],
        json_schema_extra={
            "shapes": "Annotated[float, Field(ge=0)]",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.weight_decay",
            "classification": "input",
        },
    )
    seed: StrictInt = Field(
        default=0,
        description="Целочисленный seed нативного обучения.",
        examples=[0],
        json_schema_extra={
            "shapes": "StrictInt",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.seed",
            "classification": "input",
        },
    )
    pretrained: StrictBool = Field(
        default=True,
        description=(
            "Использовать поддерживаемые предварительно обученные веса. false "
            "разрешает обучение без их загрузки."
        ),
        examples=[True],
        json_schema_extra={
            "shapes": "StrictBool",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.pretrained",
            "classification": "input",
        },
    )
    weights: Path | None = Field(
        default=None,
        description=(
            "Явный локальный checkpoint для дообучения. Имеет приоритет над "
            "автоматической подготовкой именованных весов."
        ),
        examples=["weights/best.pth"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.weights",
            "classification": "input",
        },
    )
    backbone_weights: Path | None = Field(
        default=None,
        description=(
            "Локальные веса backbone для DEIMv2, Faster R-CNN или FCOS. RF-DETR "
            "не поддерживает отдельные backbone_weights."
        ),
        examples=["weights/backbone.pth"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.backbone_weights",
            "classification": "input",
        },
    )
    amp: StrictBool = Field(
        default=True,
        description=(
            "Включить смешанную точность нативного обучения, если она "
            "поддерживается устройством и адаптером."
        ),
        examples=[True],
        json_schema_extra={
            "shapes": "StrictBool",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.amp",
            "classification": "input",
        },
    )
    grad_accum_steps: Annotated[int, Field(strict=True, gt=0)] = Field(
        default=1,
        description=(
            "Положительное число шагов накопления градиента. DEIMv2 поддерживает только 1."
        ),
        examples=[1],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)]",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.grad_accum_steps",
            "classification": "input",
        },
    )
    use_ema: StrictBool = Field(
        default=True,
        description=(
            "Использовать экспоненциальное усреднение весов в поддерживающем его нативном тренере."
        ),
        examples=[True],
        json_schema_extra={
            "shapes": "StrictBool",
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.use_ema",
            "classification": "input",
        },
    )
    augmentation: (
        DeimAugmentationOverrides | RFDETRAugmentationOverrides | EmptyAugmentationOverrides | None
    ) = Field(
        default=None,
        description=(
            "Карта отключаемых нативных аугментаций для "
            "transforms=albumentations; схема зависит от backend. В "
            "native-профиле должна быть null."
        ),
        examples=[None],
        json_schema_extra={
            "shapes": (
                "DeimAugmentationOverrides | RFDETRAugmentationOverrides | "
                "EmptyAugmentationOverrides | None"
            ),
            "applicability": "TrainSettings",
            "source": "clearml_yolo.core.models.TrainSettings.augmentation",
            "classification": "input",
        },
    )


class PredictSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: Device = Field(
        default=None,
        description=(
            "Независимый выбор устройства предсказания; null оставляет решение нативному адаптеру."
        ),
        examples=["cpu"],
        json_schema_extra={
            "shapes": "Device",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.device",
            "classification": "input",
        },
    )
    batch: Annotated[int, Field(strict=True, gt=0)] = Field(
        default=1,
        description="Положительное число изображений в пакете предсказания.",
        examples=[1],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)]",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.batch",
            "classification": "input",
        },
    )
    imgsz: ImageSize | None = Field(
        default=None,
        description=(
            "Разрешение предсказания; null наследует обученное разрешение "
            "checkpoint. RF-DETR требует квадрат, кратный 32."
        ),
        examples=[640],
        json_schema_extra={
            "shapes": "ImageSize | None",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.imgsz",
            "classification": "input",
        },
    )
    conf: Annotated[float, Field(ge=0, le=1)] = Field(
        default=0.001,
        description=(
            "Минимальная уверенность сохраняемых детекций от 0 до 1. Для "
            "последующей калибровки оставляйте низкий порог."
        ),
        examples=[0.001],
        json_schema_extra={
            "shapes": "Annotated[float, Field(ge=0, le=1)]",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.conf",
            "classification": "input",
        },
    )
    iou: Annotated[float, Field(gt=0, le=1)] = Field(
        default=0.7,
        description="Порог IoU подавления пересекающихся детекций, строго больше 0 и не больше 1.",
        examples=[0.7],
        json_schema_extra={
            "shapes": "Annotated[float, Field(gt=0, le=1)]",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.iou",
            "classification": "input",
        },
    )
    max_det: Annotated[int, Field(strict=True, gt=0)] = Field(
        default=300,
        description="Положительное максимальное количество детекций на изображение.",
        examples=[300],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)]",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.max_det",
            "classification": "input",
        },
    )
    half: StrictBool = Field(
        default=False,
        description=(
            "Использовать FP16 при предсказании, если это поддерживают устройство и адаптер."
        ),
        examples=[False],
        json_schema_extra={
            "shapes": "StrictBool",
            "applicability": "PredictSettings",
            "source": "clearml_yolo.core.models.PredictSettings.half",
            "classification": "input",
        },
    )


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: BackendName = Field(
        default="ultralytics",
        description=(
            "Семейство детектора. Для Ultralytics активны группы ultralytics и ultralytics_predict."
        ),
        examples=["rfdetr"],
        json_schema_extra={
            "shapes": "BackendName",
            "applicability": "ModelConfig",
            "source": "clearml_yolo.core.models.ModelConfig.backend",
            "classification": "input",
        },
    )
    preset: str = Field(
        default="default",
        description=(
            "Зарегистрированная архитектура выбранного семейства; определяет "
            "исходное разрешение обучения."
        ),
        examples=["small"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "ModelConfig",
            "source": "clearml_yolo.core.models.ModelConfig.preset",
            "classification": "input",
        },
    )
    source_dir: Path | None = Field(
        default=None,
        description=(
            "Каталог исходников DEIMv2; null разрешает штатную подготовку. Для "
            "других семейств запрещён."
        ),
        examples=["vendor/DEIMv2"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ModelConfig",
            "source": "clearml_yolo.core.models.ModelConfig.source_dir",
            "classification": "input",
        },
    )
    train: TrainSettings = Field(
        default_factory=TrainSettings,
        description=(
            "Параметры обучения не-YOLO детекторов. Для Ultralytics оставьте "
            "значения по умолчанию и настройте ultralytics."
        ),
        examples=[{"epochs": 10}],
        json_schema_extra={
            "shapes": "TrainSettings",
            "applicability": "ModelConfig",
            "source": "clearml_yolo.core.models.ModelConfig.train",
            "classification": "input",
        },
    )
    predict: PredictSettings = Field(
        default_factory=PredictSettings,
        description=(
            "Параметры предсказания не-YOLO детекторов. Для Ultralytics "
            "используйте ultralytics_predict."
        ),
        examples=[{"batch": 2}],
        json_schema_extra={
            "shapes": "PredictSettings",
            "applicability": "ModelConfig",
            "source": "clearml_yolo.core.models.ModelConfig.predict",
            "classification": "input",
        },
    )

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
        augmentation = self.train.augmentation
        expected = {
            "deimv2": DeimAugmentationOverrides,
            "rfdetr": RFDETRAugmentationOverrides,
            "fasterrcnn": EmptyAugmentationOverrides,
            "fcos": EmptyAugmentationOverrides,
        }
        if augmentation is not None and (
            self.backend not in expected or not isinstance(augmentation, expected[self.backend])
        ):
            raise ValueError("model.train.augmentation does not match the selected backend")
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

    resize: Literal["stretch", "letterbox", "shortest_edge"] = Field(
        description=(
            "Способ изменения размера: stretch, letterbox либо shortest_edge; "
            "должен совпадать с подготовкой входа checkpoint."
        ),
        examples=["shortest_edge"],
        json_schema_extra={
            "shapes": "Literal['stretch', 'letterbox', 'shortest_edge']",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.resize",
            "classification": "input",
        },
    )
    size: ImageSize = Field(
        description="Положительное разрешение либо пара высота/ширина подготовки изображения.",
        examples=[800],
        json_schema_extra={
            "shapes": "ImageSize",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.size",
            "classification": "input",
        },
    )
    mean: tuple[float, float, float] = Field(
        default=(0.485, 0.456, 0.406),
        description="Три средних значения нормализации каналов RGB.",
        examples=[[0.485, 0.456, 0.406]],
        json_schema_extra={
            "shapes": "tuple[float, float, float]",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.mean",
            "classification": "input",
        },
    )
    std: tuple[float, float, float] = Field(
        default=(0.229, 0.224, 0.225),
        description="Три значения стандартного отклонения для нормализации каналов RGB.",
        examples=[[0.229, 0.224, 0.225]],
        json_schema_extra={
            "shapes": "tuple[float, float, float]",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.std",
            "classification": "input",
        },
    )
    stride: Annotated[int, Field(strict=True, gt=0)] = Field(
        default=32,
        description="Положительная кратность пространственных размеров, необходимая модели.",
        examples=[32],
        json_schema_extra={
            "shapes": "Annotated[int, Field(strict=True, gt=0)]",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.stride",
            "classification": "input",
        },
    )
    color: Literal["RGB"] = Field(
        default="RGB",
        description="Порядок цветовых каналов; поддерживается только RGB.",
        examples=["RGB"],
        json_schema_extra={
            "shapes": "Literal['RGB']",
            "applicability": "Preprocessing",
            "source": "clearml_yolo.core.models.Preprocessing.color",
            "classification": "input",
        },
    )


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
