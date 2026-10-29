"""Project-owned requests and results shared by workflows and their adapters."""

# ruff: noqa: RUF001 -- Public configuration documentation is intentionally Russian.

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from clearml_yolo.core.evaluation.policy import validate_thresholds
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.models import BackendName, ModelConfig, Preprocessing

DEFAULT_PROJECT_NAME = "clearml-yolo"
DatasetFormat = Literal["ndjson", "flat", "coco"]
ImageNameMode = Literal["name", "stem", "path"]
ModelSource = Literal["clearml", "local"]
PREDICTION_COLUMNS = [
    "image_name",
    "instance_label",
    "confidence",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
]


@dataclass(frozen=True)
class GroundTruthRead:
    """Original source rows and a row-aligned execution view with resolved media paths."""

    source: pd.DataFrame
    execution: pd.DataFrame


class ClearMLDatasetRef(BaseModel):
    """One immutable dataset ID or a named dataset with an optional version."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    dataset_id: str | None = Field(
        default=None,
        description=(
            "Идентификатор неизменяемой версии ClearML Dataset. Не совмещается с "
            "именованным селектором."
        ),
        examples=["dataset-id"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ClearMLDatasetRef",
            "source": "clearml_yolo.application.contracts.ClearMLDatasetRef.dataset_id",
            "classification": "input",
        },
    )
    project_name: str | None = Field(
        default=None,
        description=(
            "Имя проекта ClearML Dataset; обязательно вместе с name, когда dataset_id не задан."
        ),
        examples=["datasets"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ClearMLDatasetRef",
            "source": "clearml_yolo.application.contracts.ClearMLDatasetRef.project_name",
            "classification": "input",
        },
    )
    name: str | None = Field(
        default=None,
        description=(
            "Имя набора ClearML Dataset; обязательно вместе с project_name при поиске по имени."
        ),
        examples=["inspection"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ClearMLDatasetRef",
            "source": "clearml_yolo.application.contracts.ClearMLDatasetRef.name",
            "classification": "input",
        },
    )
    version: str | None = Field(
        default=None,
        description=(
            "Версия именованного ClearML Dataset; null оставляет выбор версии механизму ClearML."
        ),
        examples=["1.0.0"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ClearMLDatasetRef",
            "source": "clearml_yolo.application.contracts.ClearMLDatasetRef.version",
            "classification": "input",
        },
    )

    @field_validator("dataset_id", "project_name", "name", "version")
    @classmethod
    def _nonempty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Dataset selector values must not be empty")
        return value

    @model_validator(mode="after")
    def _one_selector(self) -> Self:
        if self.dataset_id is not None:
            if any(value is not None for value in (self.project_name, self.name, self.version)):
                raise ValueError("dataset_id cannot be combined with project_name, name or version")
        elif self.project_name is None or self.name is None:
            raise ValueError("Ground truth requires dataset_id or both project_name and name")
        return self


@dataclass(frozen=True)
class ResolvedGroundTruth:
    """CSV path and original dataset identity, retained through derived stage inputs."""

    path: Path
    dataset_id: str | None = None
    project_name: str | None = None
    name: str | None = None
    version: str | None = None
    csv_sha256: str | None = None


type GroundTruthInput = str | Path | ClearMLDatasetRef | Mapping[str, object] | ResolvedGroundTruth


class ClearMLConfig(BaseModel):
    """Identity of the ClearML experiment this run belongs to."""

    model_config = ConfigDict(extra="forbid")
    project_name: str = Field(
        default=DEFAULT_PROJECT_NAME,
        description=(
            "Проект ClearML для текущего эксперимента. Задавайте явно, чтобы "
            "разделять рабочие запуски."
        ),
        examples=["experiments"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "ClearMLConfig",
            "source": "clearml_yolo.application.contracts.ClearMLConfig.project_name",
            "classification": "input",
        },
    )
    task_name: str = Field(
        default="yolo-run",
        description=(
            "Читаемое имя задачи ClearML; влияет также на безопасное имя неявного"
            " каталога результатов."
        ),
        examples=["first-training"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "ClearMLConfig",
            "source": "clearml_yolo.application.contracts.ClearMLConfig.task_name",
            "classification": "input",
        },
    )
    task_type: str = Field(
        default="training",
        description="Тип задачи ClearML, публикуемой владельцем операции.",
        examples=["training"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "ClearMLConfig",
            "source": "clearml_yolo.application.contracts.ClearMLConfig.task_type",
            "classification": "input",
        },
    )
    tags: list[str] = Field(
        default_factory=list,
        description=(
            "Теги задачи ClearML; задавайте список строк для поиска и группировки экспериментов."
        ),
        examples=[["tutorial"]],
        json_schema_extra={
            "shapes": "list[str]",
            "applicability": "ClearMLConfig",
            "source": "clearml_yolo.application.contracts.ClearMLConfig.tags",
            "classification": "input",
        },
    )
    output_uri: str | bool | None = Field(
        default=True,
        description=(
            "Удалённое хранилище артефактов: true использует настройки ClearML, "
            "строка задаёт URI. false, null и пустая строка запрещены."
        ),
        examples=[True],
        json_schema_extra={
            "shapes": "str | bool | None",
            "applicability": "ClearMLConfig",
            "source": "clearml_yolo.application.contracts.ClearMLConfig.output_uri",
            "classification": "input",
        },
    )

    @model_validator(mode="after")
    def _validate_tracking_destination(self) -> Self:
        """Require remote artifact storage without changing explicit run identity."""
        if self.output_uri is None or self.output_uri is False or self.output_uri == "":
            raise ValueError("ClearML output_uri is required for remote artifact storage")
        return self


class PreparedDataset(BaseModel):
    """Prepared native inputs and local diagnostics, separate from run publication."""

    data: Path
    ground_truth: Path
    manifest: Path
    dataset_format: DatasetFormat
    artifacts: list[Path]
    cache_identity: str | None = None


class ScoredResolution(BaseModel):
    """Checkpoint training size and requested inference size, before native normalization."""

    trained_at: int | list[int] | None
    scored_at: int | list[int]

    @property
    def was_trained_elsewhere(self) -> bool:
        """Whether requested size differs from recorded training size before normalization."""
        return self.trained_at is not None and self.trained_at != self.scored_at

    def as_table(self) -> pd.DataFrame:
        """The pair as a two-column table, for the run record rather than for the log.

        Rendered once here because both places that keep it — the ClearML plots tab and the
        sheet appended to the dev workbook — have to say the same thing, and a reader who
        finds one of them and not the other must not get two different answers. The verdict
        is spelled out rather than left as two numbers to compare, since the whole point is
        that a reader skimming for it should not have to notice they differ.
        """
        trained = "not recorded in the checkpoint" if self.trained_at is None else self.trained_at
        if self.trained_at is None:
            verdict = "unknown: the checkpoint does not say what it was trained at"
        elif self.was_trained_elsewhere:
            verdict = "different requested size; compare the normalized predictor target"
        else:
            verdict = "yes"
        return pd.DataFrame(
            {
                "parameter": [
                    "trained at imgsz",
                    "requested inference imgsz",
                    "same requested size?",
                ],
                "value": [str(trained), str(self.scored_at), verdict],
            }
        )


class VocabularyReport(BaseModel):
    """How the checkpoint's class vocabulary lines up with the split's ground truth."""

    model_classes: list[str]
    unknown_to_model: list[str]
    unknown_to_ground_truth: list[str]


class InferenceEvidence(BaseModel):
    """Native arguments and output location captured after predictor normalization."""

    effective_args: dict[str, Any]
    save_dir: str
    requested_args: dict[str, Any] = Field(default_factory=dict)
    normalized_imgsz: list[int] | None = None
    checkpoint_design: dict[str, Any] = Field(default_factory=dict)


class PredictResult(BaseModel):
    predictions: Path
    resolution: ScoredResolution
    effective_args: dict[str, Any] = Field(default_factory=dict)
    model_identity: ModelIdentity | None = None


class TrainResult(BaseModel):
    weights: Path
    save_dir: Path
    effective_args: dict[str, Any] = Field(default_factory=dict)
    cleaned_ground_truth: Path
    dataset_reference: Path


class MetricsResult(BaseModel):
    """Dashboard workbooks and the one frozen threshold map used for each split."""

    output_dir: Path
    dashboards: dict[str, Path] = Field(default_factory=dict)
    best_confidences: dict[str, dict[str, float]] = Field(default_factory=dict)
    evaluations: dict[str, Path] = Field(default_factory=dict)


class ReportResult(BaseModel):
    """Generated workbooks keyed by the evaluated split."""

    dev_reports: dict[str, Path] = Field(default_factory=dict)
    business_reports: dict[str, Path] = Field(default_factory=dict)
    skipped_splits: list[str] = Field(default_factory=list)


class ModelRef(BaseModel):
    """A checkpoint and the exact thresholds calibrated for it."""

    model_config = ConfigDict(extra="forbid")
    source: ModelSource = Field(
        default="clearml",
        description=(
            "Источник checkpoint: clearml для поиска опубликованной модели либо local для файла."
        ),
        examples=["clearml"],
        json_schema_extra={
            "shapes": "ModelSource",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.source",
            "classification": "input",
        },
    )
    task_id: str | None = Field(
        default=None,
        description="Точный идентификатор задачи ClearML; не допускается с source=local.",
        examples=["task-id"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.task_id",
            "classification": "input",
        },
    )
    project_name: str | None = Field(
        default=None,
        description="Проект поиска задачи ClearML, если точный task_id не задан.",
        examples=["experiments"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.project_name",
            "classification": "input",
        },
    )
    task_name: str | None = Field(
        default=None,
        description="Имя задачи при поиске checkpoint в ClearML.",
        examples=["baseline"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.task_name",
            "classification": "input",
        },
    )
    tags: list[str] = Field(
        default_factory=lambda: ["prod"],
        description="Теги поиска опубликованной модели; по умолчанию выбирается prod.",
        examples=[["prod"]],
        json_schema_extra={
            "shapes": "list[str]",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.tags",
            "classification": "input",
        },
    )
    weights: Path | None = Field(
        default=None,
        description=(
            "Локальный checkpoint; обязателен для source=local и запрещён для source=clearml."
        ),
        examples=["best.pth"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.weights",
            "classification": "input",
        },
    )
    thresholds: dict[str, float] | None = Field(
        default=None,
        description=(
            "Точные пороги уверенности по именам классов, откалиброванные для "
            "этого checkpoint на val. Для local непустая карта обязательна."
        ),
        examples=[{"defect": 0.35}],
        json_schema_extra={
            "shapes": "dict[str, float] | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.thresholds",
            "classification": "input",
        },
    )
    label: str | None = Field(
        default=None,
        description=(
            "Читаемая подпись модели в сравнении; null использует разрешённую идентичность."
        ),
        examples=["baseline"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.label",
            "classification": "input",
        },
    )
    backend: BackendName | None = Field(
        default=None,
        description=(
            "Семейство нативного checkpoint; задаётся вместе с preset для "
            "проверки или описания сырых весов."
        ),
        examples=["fasterrcnn"],
        json_schema_extra={
            "shapes": "BackendName | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.backend",
            "classification": "input",
        },
    )
    preset: str | None = Field(
        default=None,
        description=(
            "Архитектура checkpoint из реестра выбранного backend; backend и "
            "preset задаются вместе."
        ),
        examples=["resnet50_fpn"],
        json_schema_extra={
            "shapes": "str | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.preset",
            "classification": "input",
        },
    )
    source_dir: Path | None = Field(
        default=None,
        description=(
            "Путь к исходникам DEIMv2 для сырых checkpoint; требует backend и "
            "preset, для остальных семейств запрещён."
        ),
        examples=["vendor/DEIMv2"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.source_dir",
            "classification": "input",
        },
    )
    class_names: tuple[str, ...] | None = Field(
        default=None,
        description=(
            "Имена foreground-классов сырых весов в порядке выходов модели. "
            "Требуют backend и preset."
        ),
        examples=[["defect"]],
        json_schema_extra={
            "shapes": "tuple[str, ...] | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.class_names",
            "classification": "input",
        },
    )
    preprocessing: Preprocessing | None = Field(
        default=None,
        description=(
            "Явная схема подготовки изображений для сырых checkpoint. Требует "
            "backend и preset; не меняет обученные веса."
        ),
        examples=[{"resize": "shortest_edge", "size": 800}],
        json_schema_extra={
            "shapes": "Preprocessing | None",
            "applicability": "ModelRef",
            "source": "clearml_yolo.application.contracts.ModelRef.preprocessing",
            "classification": "input",
        },
    )

    @model_validator(mode="after")
    def _validate_source(self) -> Self:
        if (self.backend is None) != (self.preset is None):
            raise ValueError("Checkpoint backend and preset must be specified together")
        if self.backend is not None:
            ModelConfig.model_validate(
                {"backend": self.backend, "preset": self.preset, "source_dir": self.source_dir}
            )
        elif any(
            value is not None for value in (self.source_dir, self.class_names, self.preprocessing)
        ):
            raise ValueError("Raw checkpoint metadata requires backend and preset")
        if self.source == "local":
            if self.weights is None:
                raise ValueError("source='local' requires weights")
            if not self.thresholds:
                raise ValueError("source='local' requires exact thresholds")
            if self.task_id is not None:
                raise ValueError("source='local' cannot specify a ClearML task_id")
        elif self.weights is not None:
            raise ValueError("source='clearml' cannot specify local weights")
        if self.thresholds is not None:
            self.thresholds = validate_thresholds(self.thresholds, list(self.thresholds))
        return self


class ResolvedModel(BaseModel):
    """A model reference after lookup, with its exact provenance retained."""

    source: ModelSource
    weights: Path
    thresholds: dict[str, float]
    task_id: str | None = None
    links: dict[str, str] = Field(default_factory=dict)
    identity: ModelIdentity | None = None
    backend_assertions: dict[str, Any] = Field(default_factory=dict)


class InferenceConfig(BaseModel):
    """Native inference settings applied identically to both checkpoints."""

    model_config = ConfigDict(extra="forbid")
    conf: float | None
    iou: float
    imgsz: int | list[int]
    batch: int
    device: str | int | list[int] | None
    image_name: Literal["name"] = "name"
    reuse_existing: bool = True
    ultralytics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _no_duplicate_native_keys(self) -> Self:
        fixed = {
            "batch",
            "conf",
            "device",
            "image_name",
            "imgsz",
            "iou",
            "mode",
            "model",
            "name",
            "project",
            "save_dir",
            "source",
            "stream",
            "task",
        }
        overlap = sorted(fixed & set(self.ultralytics))
        if overlap:
            raise ValueError(f"inference.ultralytics duplicates explicit key(s): {overlap}")
        return self


class SettledInference(BaseModel):
    """Validated inference settings shared by both checkpoints."""

    conf: float | None
    iou: float
    imgsz: int | list[int]
    batch: int
    device: str | int | list[int] | None
    image_name: Literal["name"]
    reuse_existing: bool
    ultralytics: dict[str, Any] = Field(default_factory=dict)


class ComparisonManifest(BaseModel):
    split: str
    baseline_dashboard: str
    candidate_dashboard: str
    baseline_predictions: str
    candidate_predictions: str
    statistical_workbook: str
    baseline_identity: ModelIdentity | None = None
    candidate_identity: ModelIdentity | None = None


class CompareResult(BaseModel):
    """Statistical report plus the paired inputs for developer/business reports."""

    workbook: Path
    baseline_dashboard: Path
    candidate_dashboard: Path
    baseline_predictions: Path
    candidate_predictions: Path
    manifest: Path
    classes_compared: int
    classes_excluded: int
    degraded_classes: list[str] = Field(default_factory=list)
