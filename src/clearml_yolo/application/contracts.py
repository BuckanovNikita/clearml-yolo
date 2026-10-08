"""Project-owned requests and results shared by workflows and their adapters."""

from pathlib import Path
from typing import Any, Literal, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from clearml_yolo.core.evaluation.policy import validate_thresholds
from clearml_yolo.core.identity import ModelIdentity

DEFAULT_PROJECT_NAME = "clearml-yolo"
DatasetFormat = Literal["ndjson", "flat"]
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


class ClearMLConfig(BaseModel):
    """Identity of the ClearML experiment this run belongs to."""

    model_config = ConfigDict(extra="forbid")
    project_name: str = DEFAULT_PROJECT_NAME
    task_name: str = "yolo-run"
    task_type: str = "training"
    tags: list[str] = Field(default_factory=list)
    output_uri: str | bool | None = True

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


class ScoredResolution(BaseModel):
    """Checkpoint training size and requested inference size, before native normalization."""

    trained_at: int | None
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
    source: ModelSource = "clearml"
    task_id: str | None = None
    project_name: str | None = None
    task_name: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["prod"])
    weights: Path | None = None
    thresholds: dict[str, float] | None = None
    label: str | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> Self:
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


class InferenceConfig(BaseModel):
    """Native inference settings applied identically to both checkpoints."""

    model_config = ConfigDict(extra="forbid")
    conf: float | None
    iou: float
    imgsz: int | list[int]
    batch: int
    device: str | int | list[int] | None
    image_name: ImageNameMode = "name"
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
    image_name: ImageNameMode
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
