"""Score one split at fixed per-class confidence thresholds.

digital-metrics exposes no public way to score at thresholds that were solved
elsewhere: ``Evaluation`` either calibrates in-sample or on a held-out split, and
its threshold search is private. Comparing two models fairly needs the opposite —
the same split scored twice at each model's own frozen production thresholds — so
this module composes the public sub-package functions (``match_boxes`` then
``slice_by_conf``) and does its own tally.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import pandas as pd
from digital_metrics.engines import compute_metrics_from_matches
from digital_metrics.matching import compute_iou_matrix, find_duplicates_bboxes, match_boxes
from digital_metrics.preprocess import PredictionPreprocessor
from digital_metrics.reporting import get_dashboards
from digital_metrics.scoring import (
    compute_map,
    find_best_confidences,
    find_best_global_confidence,
    get_confusion_matrix,
    slice_by_conf,
)
from digital_metrics.validation import validate_dataframes
from loguru import logger
from pydantic import BaseModel, ConfigDict

BBOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
PLOT_METRICS = ("recall", "precision", "perebrak", "nedobrak")


class EvaluationConfig(BaseModel):
    """Settings applied identically during calibration and fixed scoring."""

    model_config = ConfigDict(extra="forbid")

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


class MatchRecord(Protocol):
    """Fields used from digital-metrics' runtime match objects."""

    type: str
    gt_index: int
    pred_index: int


def validate_thresholds(
    thresholds: Mapping[str, float | int], required_classes: list[str]
) -> dict[str, float]:
    """Return exact numeric thresholds after validating every required class."""
    missing = sorted(set(required_classes) - set(thresholds))
    if missing:
        raise ValueError(f"Confidence thresholds are missing required class(es): {missing}")

    normalized = {str(name): float(value) for name, value in thresholds.items()}
    nonfinite = sorted(name for name, value in normalized.items() if not math.isfinite(value))
    if nonfinite:
        raise ValueError(f"Confidence thresholds must be finite for class(es): {nonfinite}")
    outside = sorted(name for name, value in normalized.items() if not 0.0 <= value <= 1.0)
    if outside:
        raise ValueError(
            f"Confidence thresholds must be within [0, 1] for class(es): {outside}"
        )
    return normalized


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
class EvaluatedSplit:
    """One fixed-threshold evaluation shared by every downstream report."""

    split: str
    image_names: list[str]
    thresholds: dict[str, float]
    metrics: dict[str, Any]
    outcome: SplitOutcome
    dashboard: pd.DataFrame
    dtrk_dashboard: pd.DataFrame
    dashboard_path: Path
    dtrk_dashboard_path: Path
    plot_paths: dict[str, Path]
    confusion_matrix_path: Path
    gt_matches: pd.DataFrame
    pred_matches: pd.DataFrame


def classes_from_ground_truth(ground_truth: pd.DataFrame) -> list[str]:
    """Return the real class vocabulary, excluding empty-image placeholders."""
    if "instance_label" not in ground_truth.columns:
        raise ValueError("Ground truth is missing the 'instance_label' column")
    return sorted({str(value) for value in ground_truth["instance_label"].dropna().unique()})


def validate_split_membership(ground_truth: pd.DataFrame) -> None:
    """Reject leakage when one logical image appears in both validation and test."""
    required = {"image_name", "split"}
    missing = sorted(required - set(ground_truth.columns))
    if missing:
        raise ValueError(f"Ground truth is missing membership column(s): {missing}")
    val_images = set(ground_truth.loc[ground_truth["split"] == "val", "image_name"])
    test_images = set(ground_truth.loc[ground_truth["split"] == "test", "image_name"])
    overlap = sorted(str(value) for value in val_images & test_images)
    if overlap:
        raise ValueError(
            "A logical image cannot belong to both val and test; overlapping image_name(s): "
            f"{overlap}"
        )


def _split_ground_truth(ground_truth: pd.DataFrame, split: str) -> pd.DataFrame:
    if "split" not in ground_truth.columns:
        raise ValueError("Ground truth is missing the 'split' column")
    selected = ground_truth[ground_truth["split"] == split].copy().reset_index(drop=True)
    if selected.empty:
        available = sorted({str(value) for value in ground_truth["split"].dropna().unique()})
        raise ValueError(f"Split {split!r} has no ground-truth rows; available splits: {available}")
    return selected


def prepare_ground_truth(ground_truth: pd.DataFrame, *, deduplicate: bool) -> pd.DataFrame:
    """Apply digital-metrics' optional duplicate-box preprocessing."""
    frame = deepcopy(ground_truth)
    validate_split_membership(frame)
    if not deduplicate:
        return frame.reset_index(drop=True)
    duplicates: list[int] = []
    for image_name in frame["image_name"].unique():
        image = frame[frame["image_name"] == image_name].dropna(subset=BBOX_COLUMNS)
        if image.empty:
            continue
        boxes = image[BBOX_COLUMNS].to_numpy(np.float64)
        duplicate_positions, _ = find_duplicates_bboxes(compute_iou_matrix(boxes, boxes))
        duplicates.extend(image.iloc[duplicate_positions].index.tolist())
    return frame.drop(duplicates).reset_index(drop=True)


def prepare_predictions(
    predictions: pd.DataFrame,
    *,
    preprocess_conf_threshold: float | None,
    preprocess_nms_containment_threshold: float | None,
    preprocess_nms_iou_threshold: float | None,
) -> pd.DataFrame:
    """Apply the same optional prediction preprocessing as Evaluation."""
    preprocessor = PredictionPreprocessor(
        conf_threshold=preprocess_conf_threshold,
        nms_containment_threshold=preprocess_nms_containment_threshold,
        nms_iou_threshold=preprocess_nms_iou_threshold,
    )
    processed = preprocessor.process(predictions.copy())
    return cast(pd.DataFrame, processed).reset_index(drop=True)


def calibrate_thresholds(
    ground_truth: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    calibration_split: str,
    classes: list[str],
    iou_threshold: float,
    matching_strategy: str,
    confidence_optimization: str,
) -> dict[str, float]:
    """Calibrate once on one split, preserving empty images in the match scope."""
    try:
        calibration_gt = _split_ground_truth(ground_truth, calibration_split)
    except ValueError as error:
        raise ValueError(
            f"No ground-truth rows for calibration split {calibration_split!r}"
        ) from error
    validate_dataframes(predictions, calibration_gt)
    image_names = [str(value) for value in calibration_gt["image_name"].unique()]
    matches = match_boxes(
        calibration_gt,
        predictions,
        iou_threshold,
        strategy=matching_strategy,
        split_image_names=image_names,
    )
    if confidence_optimization == "global":
        threshold = find_best_global_confidence(matches, classes)
        calibrated = dict.fromkeys(classes, threshold)
    elif confidence_optimization == "per_class":
        calibrated = find_best_confidences(matches, classes)
    else:
        raise ValueError(
            "confidence_optimization must be 'per_class' or 'global', got "
            f"{confidence_optimization!r}"
        )
    return validate_thresholds(calibrated, classes)


def _outcome_from_matches(
    gt_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    classes: list[str],
    sliced: dict[str, list[MatchRecord]],
) -> SplitOutcome:
    counts: dict[str, ClassCounts] = {}
    detected_gt_indices: set[int] = set()
    surviving_predictions: list[tuple[int, bool]] = []

    for class_name in classes:
        tally = ClassCounts()
        for match in sliced.get(class_name, []):
            record_type = match.type
            if record_type == "TP":
                tally.tp += 1
                detected_gt_indices.add(match.gt_index)
            elif record_type == "FP":
                tally.fp += 1
            else:
                tally.fn += 1
            if match.pred_index != -1:
                surviving_predictions.append((match.pred_index, record_type == "TP"))
        counts[class_name] = tally

    scored_gt = gt_df.dropna(subset=BBOX_COLUMNS)
    scored_gt = scored_gt[scored_gt["instance_label"].isin(classes)]
    gt_status = pd.DataFrame(
        {
            "gt_index": scored_gt.index.to_numpy(),
            "image_name": scored_gt["image_name"].to_numpy(),
            "instance_label": scored_gt["instance_label"].to_numpy(),
            "detected": scored_gt.index.isin(list(detected_gt_indices)),
        }
    ).astype({"gt_index": int, "detected": bool})

    surviving_predictions.sort()
    pred_indices = [pred_index for pred_index, _ in surviving_predictions]
    joined_preds = preds_df.loc[pred_indices, ["image_name", "instance_label"]]
    pred_status = pd.DataFrame(
        {
            "pred_index": pred_indices,
            "image_name": joined_preds["image_name"].to_numpy(),
            "instance_label": joined_preds["instance_label"].to_numpy(),
            "is_tp": [is_tp for _, is_tp in surviving_predictions],
        }
    ).astype({"pred_index": int, "is_tp": bool})
    return SplitOutcome(counts=counts, gt_status=gt_status, pred_status=pred_status)


def _visualization_frames(
    gt_df: pd.DataFrame, preds_df: pd.DataFrame, outcome: SplitOutcome
) -> tuple[pd.DataFrame, pd.DataFrame]:
    gt_types = outcome.gt_status.set_index("gt_index")["detected"].map(
        {True: "TP", False: "FN"}
    )
    pred_types = outcome.pred_status.set_index("pred_index")["is_tp"].map(
        {True: "TP", False: "FP"}
    )
    gt = gt_df.copy()
    gt["predict_type"] = [gt_types.get(index, "FN") for index in gt.index]
    preds = preds_df.copy()
    preds["predict_type"] = [pred_types.get(index, "filtered") for index in preds.index]
    return gt, preds


def evaluate_split(
    ground_truth: pd.DataFrame,
    raw_predictions: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    split: str,
    classes: list[str],
    thresholds: Mapping[str, float | int],
    required_classes: list[str] | None,
    iou_threshold: float,
    matching_strategy: str,
    ap_method: str,
    skip_cohen_kappa: bool,
    output_dir: Path,
    suffix: str,
    dashboard_classes: set[str] | None = None,
) -> EvaluatedSplit:
    """Score a split at an already-frozen mapping and write its dashboards."""
    if not skip_cohen_kappa:
        raise ValueError("Fixed evaluation currently requires skip_cohen_kappa=True")
    required = classes if required_classes is None else required_classes
    normalized = validate_thresholds(thresholds, required)
    gt_df = _split_ground_truth(ground_truth, split)
    validate_dataframes(predictions, gt_df)
    image_names = [str(value) for value in gt_df["image_name"].unique()]
    matches = match_boxes(
        gt_df,
        predictions,
        iou_threshold,
        strategy=matching_strategy,
        split_image_names=image_names,
    )
    sliced = cast(dict[str, list[MatchRecord]], slice_by_conf(matches, classes, normalized))
    metrics: dict[str, Any] = compute_metrics_from_matches(sliced, classes, normalized)
    gt_boxes = gt_df.dropna(subset=BBOX_COLUMNS)
    compute_map(
        gt_boxes,
        raw_predictions,
        metrics,
        image_names,
        method=ap_method,
        strategy=matching_strategy,
    )
    cm, class_labels = get_confusion_matrix(sliced, classes)
    outcome = _outcome_from_matches(gt_df, predictions, classes, sliced)

    visible_metrics = (
        metrics
        if dashboard_classes is None
        else {name: metric for name, metric in metrics.items() if name in dashboard_classes}
    )
    if not visible_metrics:
        raise ValueError(f"Split {split!r} has no classes that can be written to a dashboard")
    output_dir.mkdir(parents=True, exist_ok=True)
    dashboard, dtrk_dashboard = get_dashboards(
        visible_metrics,
        ground_truth,
        cm,
        class_labels,
        suffix=suffix,
        save_to_excel=True,
        path=str(output_dir),
    )
    dashboard_path = output_dir / f"full_dashboard_{suffix}.xlsx"
    dtrk_path = output_dir / f"метрики_дтрк_{suffix}.xlsx"
    plot_paths: dict[str, Path] = {}
    for metric_name in PLOT_METRICS:
        generated = output_dir / f"{metric_name}_confidence_intervals.png"
        preserved = output_dir / f"{metric_name}_confidence_intervals_{suffix}.png"
        generated.replace(preserved)
        plot_paths[metric_name] = preserved
    confusion_matrix_path = output_dir / f"matrix_{suffix}.xlsx"
    gt_matches, pred_matches = _visualization_frames(gt_df, predictions, outcome)
    return EvaluatedSplit(
        split=split,
        image_names=image_names,
        thresholds=normalized,
        metrics=metrics,
        outcome=outcome,
        dashboard=dashboard,
        dtrk_dashboard=dtrk_dashboard,
        dashboard_path=dashboard_path,
        dtrk_dashboard_path=dtrk_path,
        plot_paths=plot_paths,
        confusion_matrix_path=confusion_matrix_path,
        gt_matches=gt_matches,
        pred_matches=pred_matches,
    )


def score_split(
    gt_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    classes: list[str],
    thresholds: dict[str, float],
    *,
    iou_threshold: float,
    matching_strategy: str,
) -> SplitOutcome:
    """Match boxes once, threshold each class at its frozen confidence, then tally.

    A class missing from ``thresholds`` is scored at 0.0, mirroring
    ``slice_by_conf``. Ground-truth rows whose label is outside ``classes`` are
    excluded from ``gt_status``, because ``slice_by_conf`` drops their records and
    their status would otherwise be unknowable rather than merely undetected.

    ``gt_status`` is built from every scored ground-truth row rather than from the
    match records: under the ``greedy`` strategy a ground-truth box consumed by a
    cross-class match produces no record at all, so a record-derived pass would
    drop it from the recall denominator entirely. Under the default ``iou_prior``
    strategy every ground-truth box does yield its own record, so there
    ``len(gt_status)`` equals ``tp + fn`` and the two recalls coincide.

    Only a class's own TP record marks a ground-truth box detected. A cross-class
    false positive also carries a ``gt_index``, but that box's real status is
    recorded by its own TP or FN record.
    """
    for frame_name, frame in (("Ground-truth", gt_df), ("Prediction", preds_df)):
        if not frame.index.is_unique:
            raise ValueError(
                f"{frame_name} index has duplicate labels, so match records cannot join back."
            )
        if (frame.index < 0).any():
            raise ValueError(
                f"{frame_name} index has negative labels, which collide with the -1 that match "
                "records use for 'no associated box'."
            )

    # Placeholder rows for empty images (no label, no bbox) must stay in the image
    # list so predictions on those images are still counted as false positives.
    split_image_names = gt_df["image_name"].unique().tolist()
    matches = match_boxes(
        gt_df,
        preds_df,
        iou_threshold,
        strategy=matching_strategy,
        split_image_names=split_image_names,
    )
    sliced = cast(dict[str, list[MatchRecord]], slice_by_conf(matches, classes, thresholds))

    scored_gt = gt_df.dropna(subset=BBOX_COLUMNS)
    unknown_labels = sorted(set(scored_gt["instance_label"]) - set(classes), key=str)
    if unknown_labels:
        logger.warning(
            "Ground truth carries label(s) {} outside the scored classes {}; "
            "those boxes are excluded from the outcome.",
            unknown_labels,
            classes,
        )
    outcome = _outcome_from_matches(gt_df, preds_df, classes, sliced)
    logger.debug(
        "Scored {} ground-truth boxes and {} surviving predictions over {} classes",
        len(outcome.gt_status),
        len(outcome.pred_status),
        len(classes),
    )
    return outcome
