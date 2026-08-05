"""Score predictions per split and publish dashboards to ClearML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_dataframe

DASHBOARD_PREFIX = "full_dashboard"


class EvaluationConfig(BaseModel):
    """Knobs forwarded to digital-metrics' Evaluation."""

    iou_threshold: float = 0.5
    matching_strategy: str = "iou_prior"
    ap_method: str = "interp"
    confidence_optimization: str = "per_class"
    skip_cohen_kappa: bool = True
    preprocess: bool = False
    preprocess_preds_conf_threshold: float | None = None
    preprocess_preds_nms_containment_threshold: float | None = None
    preprocess_preds_nms_iou_threshold: float | None = None
    backend: str | None = None


class MetricsResult(BaseModel):
    """Where each split's dashboard workbook ended up, and at what thresholds.

    ``best_confidences`` carries the per-class thresholds each split was calibrated at,
    keyed by split. They are the numbers a later comparison has to score this model at,
    and they are returned rather than read back from ClearML so the comparison works at
    full precision and with tracking switched off.
    """

    output_dir: Path
    dashboards: dict[str, Path] = Field(default_factory=dict)
    best_confidences: dict[str, dict[str, float]] = Field(default_factory=dict)


def _log_split_scalars(task: Any, split: str, summary: dict[str, float]) -> None:
    if task is None:
        return
    logger_ = task.get_logger()
    for metric, value in summary.items():
        logger_.report_scalar(title="metrics", series=f"{split}/{metric}", value=value, iteration=0)


def _evaluate_split(
    split: str,
    preds: pd.DataFrame,
    ground_truth: pd.DataFrame,
    config: EvaluationConfig,
    calibration_split: str | None,
    output_dir: Path,
    task: Any,
) -> tuple[Path, dict[str, float]] | None:
    """Score one split and upload its artifacts.

    Returns the dashboard workbook and the thresholds the split was scored at, or None
    when the split produced no metrics at all.
    """
    from digital_metrics import Evaluation, summarize_metrics

    # A fresh Evaluation per split: calling an existing one again overwrites metrics,
    # the confusion matrix and the calibrated thresholds.
    evaluation = Evaluation(
        preds,
        ground_truth,
        iou_threshold=config.iou_threshold,
        matching_strategy=config.matching_strategy,
        ap_method=config.ap_method,
        confidence_optimization=config.confidence_optimization,
        skip_cohen_kappa=config.skip_cohen_kappa,
        preprocess=config.preprocess,
        preprocess_preds_conf_threshold=config.preprocess_preds_conf_threshold,
        preprocess_preds_nms_containment_threshold=(
            config.preprocess_preds_nms_containment_threshold
        ),
        preprocess_preds_nms_iou_threshold=config.preprocess_preds_nms_iou_threshold,
        backend=config.backend,
    )
    evaluation.suffix = split
    # Calibrating a split against itself is rejected as a leak, so the calibration
    # split scores with thresholds solved on its own data instead.
    if calibration_split == split:
        evaluation(split=split, find_best_confs=True)
    else:
        evaluation(split=split, calibration_split=calibration_split)

    if not evaluation.metrics:
        logger.warning("Split {!r} produced no metrics; skipping it", split)
        return None

    devs, dtrk = evaluation.get_dashboards(save_to_excel=True, path=str(output_dir))
    upload_dataframe(task, f"dashboard_full_{split}", devs)
    upload_dataframe(task, f"dashboard_dtrk_{split}", dtrk)

    # Thresholds were already solved during the call above; re-solving them here would
    # cost another sweep and could drift from the ones the dashboards were built with.
    visualization_gt, visualization_preds = evaluation.get_dfs_visualization(find_best_confs=False)
    upload_dataframe(task, f"matches_gt_{split}", visualization_gt)
    upload_dataframe(task, f"matches_preds_{split}", visualization_preds)

    per_class, summary = summarize_metrics(evaluation.metrics)
    upload_dataframe(task, f"metrics_summary_{split}", per_class)
    _log_split_scalars(task, split, summary)

    if task is not None:
        task.upload_artifact(
            name=f"metrics_raw_{split}",
            artifact_object={
                class_name: metric.model_dump() for class_name, metric in evaluation.metrics.items()
            },
        )
        task.upload_artifact(
            name=f"best_confidences_{split}", artifact_object=evaluation.best_confidences
        )

    dashboard = output_dir / f"{DASHBOARD_PREFIX}_{split}.xlsx"
    logger.info(
        "Split {!r}: {} classes, mean f1 {:.4f} -> {}",
        split,
        len(evaluation.metrics),
        summary.get("mean_f1_score", float("nan")),
        dashboard,
    )
    thresholds = {
        str(class_name): float(confidence)
        for class_name, confidence in dict(evaluation.best_confidences).items()
    }
    return dashboard, thresholds


def compute_metrics(
    predictions: str | Path,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    calibration_split: str | None = "val",
) -> MetricsResult:
    """Evaluate every requested split, writing one dashboard workbook per split."""
    task = init_task(clearml, stage="metrics")
    splits = splits or ["train", "val", "test"]

    preds_frame = pd.read_csv(predictions)
    ground_truth_frame = pd.read_csv(ground_truth)

    known_splits = set(ground_truth_frame.get("split", pd.Series(dtype=str)).unique())
    missing = [split for split in splits if split not in known_splits and split != "all"]
    if missing:
        logger.warning(
            "Ground truth has no rows for split(s) {}; available: {}",
            missing,
            sorted(known_splits),
        )

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    result = MetricsResult(output_dir=destination)
    for split in splits:
        scored = _evaluate_split(
            split,
            preds_frame,
            ground_truth_frame,
            evaluation,
            calibration_split,
            destination,
            task,
        )
        if scored is not None:
            result.dashboards[split], result.best_confidences[split] = scored

    if not result.dashboards:
        raise RuntimeError(
            f"No split produced metrics. Requested {splits}, ground truth contains "
            f"{sorted(known_splits)}."
        )
    return result
