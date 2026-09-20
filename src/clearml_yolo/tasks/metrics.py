"""Calibrate on validation once, then score every split at frozen thresholds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from digital_metrics import summarize_metrics
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_report import report_scalars, report_table
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    expect_artifacts,
    init_task,
    upload_artifact,
)
from clearml_yolo.comparison.scoring import (
    EvaluatedSplit,
    EvaluationConfig,
    calibrate_thresholds,
    classes_from_ground_truth,
    evaluate_split,
    prepare_ground_truth,
    prepare_predictions,
)
from clearml_yolo.progress import track

DASHBOARD_PREFIX = "full_dashboard"
__all__ = ["EvaluationConfig"]


class MetricsResult(BaseModel):
    """Dashboard workbooks and the one frozen threshold map used for each split."""

    output_dir: Path
    dashboards: dict[str, Path] = Field(default_factory=dict)
    best_confidences: dict[str, dict[str, float]] = Field(default_factory=dict)


def _upload(task: Any, name: str, value: Any) -> None:
    if task is None:
        return
    upload_artifact(task, name, value)


def _publish_split(task: Any, split: str, evaluated: EvaluatedSplit) -> None:
    name = artifact_names.per_split
    _upload(task, name(artifact_names.DASHBOARD_FULL_PREFIX, split), evaluated.dashboard_path)
    _upload(task, name(artifact_names.DASHBOARD_DTRK_PREFIX, split), evaluated.dtrk_dashboard_path)
    _upload(task, name(artifact_names.MATCHES_GT_PREFIX, split), evaluated.gt_matches)
    _upload(task, name(artifact_names.MATCHES_PREDS_PREFIX, split), evaluated.pred_matches)
    _upload(task, name("metrics_confusion_matrix", split), evaluated.confusion_matrix_path)
    for metric_name, path in evaluated.plot_paths.items():
        _upload(task, name(f"metrics_plot_{metric_name}", split), path)

    per_class, summary = summarize_metrics(evaluated.metrics)
    _upload(task, name(artifact_names.METRICS_SUMMARY_PREFIX, split), per_class)
    report_table(task, artifact_names.METRICS_SECTION, split, per_class)
    report_scalars(task, f"{artifact_names.METRICS_SECTION}_{split}", summary)
    _upload(
        task,
        name(artifact_names.METRICS_RAW_PREFIX, split),
        {class_name: metric.model_dump() for class_name, metric in evaluated.metrics.items()},
    )
    _upload(
        task,
        name(artifact_names.BEST_CONFIDENCES_PREFIX, split),
        evaluated.thresholds,
    )


def _prepare(
    predictions: pd.DataFrame,
    ground_truth: pd.DataFrame,
    config: EvaluationConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    if config.backend is not None:
        raise ValueError(
            "Frozen thresholds require the native digital-metrics backend; "
            f"backend={config.backend!r} is unsupported"
        )
    prepared_gt = prepare_ground_truth(ground_truth, deduplicate=config.preprocess)
    raw_predictions = predictions.copy().reset_index(drop=True)
    prepared_predictions = prepare_predictions(
        raw_predictions,
        preprocess_conf_threshold=config.preprocess_preds_conf_threshold,
        preprocess_nms_containment_threshold=(config.preprocess_preds_nms_containment_threshold),
        preprocess_nms_iou_threshold=config.preprocess_preds_nms_iou_threshold,
    )
    classes = sorted(
        set(classes_from_ground_truth(prepared_gt))
        | {str(value) for value in prepared_predictions["instance_label"].dropna().unique()}
    )
    if not classes:
        raise ValueError("Ground truth contains no labelled objects to evaluate")
    return prepared_gt, raw_predictions, prepared_predictions, classes


def compute_metrics(
    predictions: str | Path,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    calibration_split: str | None = "val",
) -> MetricsResult:
    """Calibrate once on validation and score requested splits at that exact mapping."""
    task = init_task(clearml, stage="metrics")
    requested = splits or ["train", "val", "test"]
    if calibration_split != "val":
        raise ValueError(
            "calibration_split must be exactly 'val'; test data must never calibrate thresholds"
        )
    if "all" in requested:
        raise ValueError("split='all' is unsupported for frozen evaluation; name concrete splits")

    expected = ["metrics_predictions", "metrics_ground_truth", "metrics_methodology"]
    for split in requested:
        expected.extend(
            [
                artifact_names.per_split(artifact_names.DASHBOARD_FULL_PREFIX, split),
                artifact_names.per_split(artifact_names.DASHBOARD_DTRK_PREFIX, split),
                artifact_names.per_split(artifact_names.MATCHES_GT_PREFIX, split),
                artifact_names.per_split(artifact_names.MATCHES_PREDS_PREFIX, split),
                artifact_names.per_split("metrics_confusion_matrix", split),
                artifact_names.per_split(artifact_names.METRICS_SUMMARY_PREFIX, split),
                artifact_names.per_split(artifact_names.METRICS_RAW_PREFIX, split),
                artifact_names.per_split(artifact_names.BEST_CONFIDENCES_PREFIX, split),
                *(
                    artifact_names.per_split(f"metrics_plot_{metric}", split)
                    for metric in ("recall", "precision", "perebrak", "nedobrak")
                ),
            ]
        )
    if task is not None:
        expect_artifacts(task, expected)

    predictions_frame = pd.read_csv(predictions, dtype={"image_name": str, "instance_label": str})
    ground_truth_frame = pd.read_csv(
        ground_truth, dtype={"image_name": str, "instance_label": str, "split": str}
    )
    _upload(task, "metrics_predictions", Path(predictions))
    _upload(task, "metrics_ground_truth", Path(ground_truth))
    prepared_gt, raw_predictions, prepared_predictions, classes = _prepare(
        predictions_frame, ground_truth_frame, evaluation
    )

    thresholds = calibrate_thresholds(
        prepared_gt,
        prepared_predictions,
        calibration_split=calibration_split,
        classes=classes,
        iou_threshold=evaluation.iou_threshold,
        matching_strategy=evaluation.matching_strategy,
        confidence_optimization=evaluation.confidence_optimization,
    )

    _upload(
        task,
        "metrics_methodology",
        {
            **evaluation.model_dump(),
            "calibration_split": "val",
            "thresholds": thresholds,
            "evaluated_splits": requested,
            "test_calibration": False,
        },
    )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result = MetricsResult(output_dir=destination)
    for split in track(requested, "Scoring splits", unit="split"):
        evaluated = evaluate_split(
            prepared_gt,
            raw_predictions,
            prepared_predictions,
            split=split,
            classes=classes,
            thresholds=thresholds,
            required_classes=classes,
            iou_threshold=evaluation.iou_threshold,
            matching_strategy=evaluation.matching_strategy,
            ap_method=evaluation.ap_method,
            skip_cohen_kappa=evaluation.skip_cohen_kappa,
            output_dir=destination,
            suffix=split,
        )
        _publish_split(task, split, evaluated)
        result.dashboards[split] = evaluated.dashboard_path
        result.best_confidences[split] = dict(evaluated.thresholds)
        _, summary = summarize_metrics(evaluated.metrics)
        logger.info(
            "Split {!r}: {} classes, mean f1 {:.4f} -> {}",
            split,
            len(evaluated.metrics),
            summary.get("mean_f1_score", float("nan")),
            evaluated.dashboard_path,
        )
    return result
