"""Compare two models on today's images, without retraining either of them.

Every input is a ClearML task or a local checkpoint, so this runs long after the
training that produced them and on a machine that has neither model on disk. Both
checkpoints are re-inferred over the *current* ground truth rather than compared through
their stored dashboards: those were computed on whatever images each run happened to
see, and differences between image sets read exactly like differences between models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo.clearml_models import fetch_best_confidences, resolve_task_weights
from clearml_yolo.clearml_report import report_comparison
from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.comparison.assemble import ComparisonTables, build_comparison_rows
from clearml_yolo.comparison.reinfer import VocabularyReport, reinfer_split
from clearml_yolo.comparison.scoring import score_split
from clearml_yolo.comparison.workbook import write_comparison_workbook
from clearml_yolo.gpu import AutoGpuConfig, resolve_inference_device

ModelSource = Literal["clearml", "local"]


class ModelRef(BaseModel):
    """One side of the comparison: a ClearML task, or a checkpoint already on disk."""

    source: ModelSource = "clearml"
    task_id: str | None = None
    weights: Path | None = None
    # Thresholds are read from the task that calibrated them. Setting them here instead
    # is for models whose metrics stage never ran.
    thresholds: dict[str, float] | None = None

    def checkpoint(self) -> Path:
        if self.source == "local":
            if self.weights is None:
                raise ValueError("source='local' needs weights=/path/to/best.pt")
            return self.weights
        if not self.task_id:
            raise ValueError("source='clearml' needs task_id=<clearml task id>")
        return resolve_task_weights(self.task_id)

    def frozen_thresholds(self, split: str) -> dict[str, float]:
        if self.thresholds is not None:
            return self.thresholds
        if self.source == "clearml" and self.task_id:
            return fetch_best_confidences(self.task_id, split)
        raise ValueError(
            "A local model carries no calibrated thresholds; set thresholds={class: conf} "
            "or point at the ClearML task whose metrics stage calibrated them."
        )


class InferenceConfig(BaseModel):
    """How both checkpoints are re-run. Identical for the two, by construction."""

    conf: float = 0.001
    iou: float = 0.7
    imgsz: int = 640
    batch: int = 16
    device: str | None = None
    image_name: str = "name"
    reuse_existing: bool = True


class CompareResult(BaseModel):
    """Where the comparison landed, and what it could not compare."""

    workbook: Path
    classes_compared: int
    classes_excluded: int
    degraded_classes: list[str] = Field(default_factory=list)


def _scored(
    weights: Path,
    ground_truth: pd.DataFrame,
    split: str,
    output: Path,
    inference: InferenceConfig,
    thresholds: dict[str, float],
    classes: list[str],
    evaluation: dict[str, Any],
) -> tuple[Any, VocabularyReport]:
    predictions, vocabulary = reinfer_split(
        weights,
        ground_truth,
        split,
        output,
        conf=inference.conf,
        iou=inference.iou,
        imgsz=inference.imgsz,
        batch=inference.batch,
        device=inference.device,
        image_name=inference.image_name,
        reuse_existing=inference.reuse_existing,
    )
    split_truth = ground_truth[ground_truth["split"] == split].reset_index(drop=True)
    outcome = score_split(
        split_truth,
        predictions.reset_index(drop=True),
        classes,
        thresholds,
        iou_threshold=evaluation["iou_threshold"],
        matching_strategy=evaluation["matching_strategy"],
    )
    return outcome, vocabulary


def _degraded(tables: ComparisonTables) -> list[str]:
    per_class = tables.rows[~tables.rows["is_pooled"].astype(bool)]
    is_degraded = per_class["precision_verdict"].eq("degraded") | per_class["recall_verdict"].eq(
        "degraded"
    )
    return [str(name) for name in per_class.loc[is_degraded, "class_name"]]


def compare(
    baseline_model: ModelRef,
    candidate_model: ModelRef,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    auto_gpu: AutoGpuConfig | None = None,
    split: str = "test",
    iou_threshold: float = 0.5,
    matching_strategy: str = "iou_prior",
    q: float = 0.05,
    bootstrap_iterations: int = 10_000,
    seed: int = 0,
) -> CompareResult:
    """Score both models on one split at their own frozen thresholds and report the diff."""
    task = init_task(clearml, stage="compare")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    if inference.device is None and auto_gpu is not None and auto_gpu.enabled:
        # Resolved once for both models: re-inferring them on different devices would put
        # a hardware difference inside a comparison that is meant to isolate the model.
        inference = inference.model_copy(update={"device": resolve_inference_device(auto_gpu)})

    truth = pd.read_csv(ground_truth)
    baseline_weights = baseline_model.checkpoint()
    candidate_weights = candidate_model.checkpoint()
    thresholds_baseline = baseline_model.frozen_thresholds(split)
    thresholds_candidate = candidate_model.frozen_thresholds(split)

    evaluation = {"iou_threshold": iou_threshold, "matching_strategy": matching_strategy}
    classes = sorted({str(label) for label in truth[truth["split"] == split]["instance_label"]})

    baseline_outcome, baseline_vocabulary = _scored(
        baseline_weights,
        truth,
        split,
        destination / f"baseline_predictions_{split}.csv",
        inference,
        thresholds_baseline,
        classes,
        evaluation,
    )
    candidate_outcome, candidate_vocabulary = _scored(
        candidate_weights,
        truth,
        split,
        destination / f"candidate_predictions_{split}.csv",
        inference,
        thresholds_candidate,
        classes,
        evaluation,
    )

    images = truth[truth["split"] == split]["image_name"].unique().tolist()
    tables = build_comparison_rows(
        baseline_outcome,
        candidate_outcome,
        thresholds_baseline=thresholds_baseline,
        thresholds_candidate=thresholds_candidate,
        images=images,
        baseline_classes=set(baseline_vocabulary.model_classes),
        candidate_classes=set(candidate_vocabulary.model_classes),
        q=q,
        iterations=bootstrap_iterations,
        seed=seed,
    )
    tables.methodology["baseline_weights"] = str(baseline_weights)
    tables.methodology["candidate_weights"] = str(candidate_weights)
    tables.methodology["split"] = split
    tables.methodology["iou_threshold"] = iou_threshold
    tables.methodology["matching_strategy"] = matching_strategy

    workbook = destination / f"comparison_{split}.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, workbook)
    report_comparison(task, split, tables.rows, tables.methodology)
    if task is not None:
        task.upload_artifact(name=f"comparison_{split}", artifact_object=workbook)

    degraded = _degraded(tables)
    logger.info(
        "Comparison of split {!r}: {} classes compared, {} excluded, {} degraded",
        split,
        len(tables.rows) - 1,
        len(tables.excluded),
        len(degraded),
    )
    return CompareResult(
        workbook=workbook,
        classes_compared=len(tables.rows) - 1,
        classes_excluded=len(tables.excluded),
        degraded_classes=degraded,
    )
