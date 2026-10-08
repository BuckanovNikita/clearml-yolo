"""Project-owned evaluation contracts shared by computation and reporting."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from clearml_yolo.core.evaluation.payload import EvaluationPayload
from clearml_yolo.core.evaluation.schema import ConfusionMatrixPayload, PRCurve
from clearml_yolo.core.identity import ModelIdentity


class EvaluationConfig(BaseModel):
    """Settings applied identically during calibration and fixed scoring."""

    model_config = ConfigDict(extra="forbid")

    iou_threshold: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    matching_strategy: Literal["greedy", "hungarian", "iou_prior"] = "iou_prior"
    ap_method: Literal["interp", "continuous"] = "interp"
    confidence_optimization: str = "per_class"
    skip_cohen_kappa: bool = True
    preprocess: bool = False
    preprocess_preds_conf_threshold: float | None = None
    preprocess_preds_nms_containment_threshold: float | None = None
    preprocess_preds_nms_iou_threshold: float | None = None
    backend: str | None = None


class DetectionMetrics(BaseModel):
    """Exact backend-produced metric values crossing the evaluation boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    counts_observed: bool
    tp: float
    fp: float
    fn: float
    confidence: float
    ap50: float
    ap75: float
    ap50_95: float
    cohen_kappa: float
    precision: float
    recall: float
    f1_score: float
    perebrak: float
    nedobrak: float
    precision_ci_lower: float
    precision_ci_upper: float
    recall_ci_lower: float
    recall_ci_upper: float
    perebrak_ci_lower: float
    perebrak_ci_upper: float
    nedobrak_ci_lower: float
    nedobrak_ci_upper: float


@dataclass(frozen=True)
class MatchResult:
    """Exact project-owned matching value; -1 denotes an absent box."""

    type: str
    gt_index: int
    pred_index: int
    gt_label: str
    pred_label: str
    confidence: float
    iou: float | None


class ClassCounts(BaseModel):
    """TP/FP/FN for one class at one fixed threshold."""

    tp: int = 0
    fp: int = 0
    fn: int = 0


@dataclass(frozen=True)
class SplitOutcome:
    """Everything one model's run over one split yields at its frozen thresholds.

    ``counts`` holds one entry per requested class, zeroed when the class is absent
    from the split. ``gt_status`` has one row per scored ground-truth box
    (``gt_index``, ``image_name``, ``instance_label``, ``detected``) and
    ``pred_status`` one row per prediction that survives thresholding
    (``pred_index``, ``image_name``, ``instance_label``, ``is_tp``). Both index
    columns are label indices into the source frames, so per-image and per-instance
    drill-downs join straight back.
    """

    counts: dict[str, ClassCounts]
    gt_status: pd.DataFrame
    pred_status: pd.DataFrame


@dataclass(frozen=True)
class ComputedEvaluation:
    """Evaluation values with no report generation or publication effects."""

    split: str
    image_names: list[str]
    thresholds: dict[str, float]
    metrics: dict[str, DetectionMetrics]
    outcome: SplitOutcome
    ground_truth: pd.DataFrame
    gt_matches: pd.DataFrame
    pred_matches: pd.DataFrame
    evaluation_payload: EvaluationPayload
    confusion_matrix: ConfusionMatrixPayload
    pr_curves: list[PRCurve]
    result_rows: pd.DataFrame
    model_identity: ModelIdentity | None = None


@dataclass(frozen=True)
class EvaluationArtifacts:
    """Rendered evaluation dashboards and owned local output paths."""

    dashboard: pd.DataFrame
    dtrk_dashboard: pd.DataFrame
    dashboard_path: Path
    dtrk_dashboard_path: Path
    plot_paths: dict[str, Path]
    confusion_matrix_path: Path


@dataclass(frozen=True)
class EvaluatedSplit:
    """One fixed-threshold evaluation shared by every downstream report."""

    split: str
    image_names: list[str]
    thresholds: dict[str, float]
    metrics: dict[str, DetectionMetrics]
    outcome: SplitOutcome
    dashboard: pd.DataFrame
    dtrk_dashboard: pd.DataFrame
    dashboard_path: Path
    dtrk_dashboard_path: Path
    plot_paths: dict[str, Path]
    confusion_matrix_path: Path
    gt_matches: pd.DataFrame
    pred_matches: pd.DataFrame
    evaluation_payload: EvaluationPayload
    confusion_matrix: ConfusionMatrixPayload
    pr_curves: list[PRCurve]
    result_rows: pd.DataFrame
    model_identity: ModelIdentity | None = None

    @classmethod
    def from_parts(
        cls,
        computed: ComputedEvaluation,
        artifacts: EvaluationArtifacts,
    ) -> "EvaluatedSplit":
        """Join the typed computational result and its rendered report."""
        return cls(
            split=computed.split,
            image_names=computed.image_names,
            thresholds=computed.thresholds,
            metrics=computed.metrics,
            outcome=computed.outcome,
            gt_matches=computed.gt_matches,
            pred_matches=computed.pred_matches,
            evaluation_payload=computed.evaluation_payload,
            confusion_matrix=computed.confusion_matrix,
            pr_curves=computed.pr_curves,
            result_rows=computed.result_rows,
            model_identity=computed.model_identity,
            dashboard=artifacts.dashboard,
            dtrk_dashboard=artifacts.dtrk_dashboard,
            dashboard_path=artifacts.dashboard_path,
            dtrk_dashboard_path=artifacts.dtrk_dashboard_path,
            plot_paths=artifacts.plot_paths,
            confusion_matrix_path=artifacts.confusion_matrix_path,
        )
