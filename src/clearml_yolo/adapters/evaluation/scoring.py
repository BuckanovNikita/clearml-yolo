"""Score one split at fixed per-class confidence thresholds.

digital-metrics exposes no public way to score at thresholds that were solved
elsewhere: ``Evaluation`` either calibrates in-sample or on a held-out split, and
its threshold search is private. Comparing two models fairly needs the opposite —
the same split scored twice at each model's own frozen production thresholds — so
this module composes the public sub-package functions (``match_boxes`` then
``slice_by_conf``) and does its own tally.
"""

import math
from collections.abc import Mapping
from copy import deepcopy
from typing import Protocol, cast

import numpy as np
import pandas as pd
from digital_metrics.engines import compute_metrics_from_matches
from digital_metrics.matching import compute_iou_matrix, find_duplicates_bboxes, match_boxes
from digital_metrics.preprocess import PredictionPreprocessor
from digital_metrics.scoring import (
    compute_map,
    find_best_confidences,
    find_best_global_confidence,
    get_confusion_matrix,
    slice_by_conf,
)
from digital_metrics.validation import REQUIRED_COLS_GT, validate_dataframes
from loguru import logger
from numpy.typing import NDArray
from pydantic import JsonValue

from clearml_yolo.adapters.evaluation.pr_curves import build_pr_curves
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core.evaluation.models import (
    ClassCounts,
    ComputedEvaluation,
    DetectionMetrics,
    EvaluationConfig,
    MatchResult,
    SplitOutcome,
)
from clearml_yolo.core.evaluation.payload import (
    ClassAveragePrecision,
    EvaluationBox,
    EvaluationBoxStatus,
    EvaluationMatch,
    EvaluationMatchStatus,
    EvaluationPayload,
    EvaluationReport,
)
from clearml_yolo.core.evaluation.policy import validate_split_membership, validate_thresholds
from clearml_yolo.core.evaluation.result_rows import assign_source_ids, build_result_rows
from clearml_yolo.core.evaluation.schema import ConfusionMatrixPayload, PRCurve
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.validation import validate_dataframe

BBOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


class _BackendMetrics(Protocol):
    """Explicit readable interface for the untyped public dependency result."""

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


class MatchRecord(Protocol):
    """Fields used from digital-metrics' runtime match objects."""

    type: str
    gt_index: int
    pred_index: int
    gt_label: str
    pred_label: str
    confidence: float
    iou: float | None


def _match_status(value: str) -> EvaluationMatchStatus:
    if value not in {"TP", "FP", "FN"}:
        raise ValueError(f"Unexpected evaluation match status: {value!r}")
    return cast(EvaluationMatchStatus, value)


def _box_coordinates(row: pd.Series) -> tuple[float, float, float, float]:
    return (
        float(row["bbox_x_tl"]),
        float(row["bbox_y_tl"]),
        float(row["bbox_x_br"]),
        float(row["bbox_y_br"]),
    )


def _integer_index(value: object) -> int:
    if not isinstance(value, (int, np.integer)):
        raise TypeError(f"Evaluation box index must be an integer, got {value!r}")
    return int(value)


def build_evaluation_payload(
    ground_truth: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    split: str,
    image_names: list[str],
    thresholds: dict[str, float],
    sliced: Mapping[str, list[MatchRecord]],
    methodology: Mapping[str, JsonValue] | None = None,
    model_identity: ModelIdentity | None = None,
) -> EvaluationPayload:
    """Convert the exact sliced match result into a neutral persisted payload."""
    records = [match for class_matches in sliced.values() for match in class_matches]
    tp_gt_indices = {match.gt_index for match in records if match.type == "TP"}
    pred_statuses: dict[int, EvaluationBoxStatus] = {
        match.pred_index: _match_status(match.type) for match in records if match.pred_index != -1
    }

    scoped_gt = ground_truth[ground_truth["image_name"].isin(image_names)]
    scored_gt = scoped_gt.dropna(subset=BBOX_COLUMNS)
    ground_truth_boxes = [
        EvaluationBox(
            index=_integer_index(index),
            image_name=str(row["image_name"]),
            label=str(row["instance_label"]),
            box=_box_coordinates(row),
            status="TP" if _integer_index(index) in tp_gt_indices else "FN",
        )
        for index, row in scored_gt.iterrows()
    ]

    scoped_predictions = predictions[predictions["image_name"].isin(image_names)]
    prediction_boxes = [
        EvaluationBox(
            index=_integer_index(index),
            image_name=str(row["image_name"]),
            label=str(row["instance_label"]),
            box=_box_coordinates(row),
            confidence=float(row["confidence"]),
            status=pred_statuses.get(_integer_index(index), "filtered"),
        )
        for index, row in scoped_predictions.iterrows()
    ]

    payload_matches = [
        EvaluationMatch(
            gt_index=None if match.gt_index == -1 else match.gt_index,
            pred_index=None if match.pred_index == -1 else match.pred_index,
            gt_label=match.gt_label,
            pred_label=match.pred_label,
            confidence=match.confidence,
            iou=match.iou,
            status=_match_status(match.type),
        )
        for match in records
    ]
    return EvaluationPayload(
        split=split,
        image_names=list(image_names),
        thresholds=dict(thresholds),
        ground_truth=ground_truth_boxes,
        predictions=prediction_boxes,
        matches=payload_matches,
        methodology=dict(methodology or {}),
        model_identity=model_identity,
    )


def _split_ground_truth(ground_truth: pd.DataFrame, split: str) -> pd.DataFrame:
    if "split" not in ground_truth.columns:
        raise ValueError("Ground truth is missing the 'split' column")
    selected = ground_truth[ground_truth["split"] == split].copy().reset_index(drop=True)
    if selected.empty:
        available = sorted({str(value) for value in ground_truth["split"].dropna().unique()})
        raise ValueError(f"Split {split!r} has no ground-truth rows; available splits: {available}")
    return selected


@trace_operation("evaluation.ground_truth.prepare")
def prepare_ground_truth(ground_truth: pd.DataFrame, *, deduplicate: bool) -> pd.DataFrame:
    """Apply digital-metrics' optional duplicate-box preprocessing."""
    frame = assign_source_ids(deepcopy(ground_truth), row_type="ground_truth")
    frame = frame.reset_index(drop=True)
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


def _prediction_coordinates(
    boxes: pd.DataFrame,
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Use upstream float conversion, isolating malformed cells only on failure."""
    nonnumeric = np.zeros(len(boxes), dtype=bool)
    try:
        return boxes.to_numpy(dtype=float, na_value=np.nan), nonnumeric
    except (TypeError, ValueError):
        coordinates = np.full(boxes.shape, np.nan)
        for row_index, row in enumerate(boxes.itertuples(index=False, name=None)):
            for column_index, value in enumerate(row):
                try:
                    coordinates[row_index, column_index] = float(value)
                except (TypeError, ValueError):
                    nonnumeric[row_index] = True
        return coordinates, nonnumeric


def filter_invalid_prediction_boxes(predictions: pd.DataFrame) -> pd.DataFrame:
    """Copy valid geometry for evaluation without changing raw prediction artifacts.

    Counts use the first applicable reason per row. Required-column errors remain
    the upstream validator's responsibility; only invalid coordinate cells and
    nonpositive extents are tolerated here.
    """
    if predictions.empty or not {*BBOX_COLUMNS, "image_name"}.issubset(predictions.columns):
        return predictions.copy()
    boxes = predictions[BBOX_COLUMNS]
    coordinates, nonnumeric = _prediction_coordinates(boxes)
    missing = boxes.isna().any(axis=1).to_numpy()
    nonnumeric &= ~missing
    nonfinite = ~np.isfinite(coordinates).all(axis=1) & ~missing & ~nonnumeric
    finite = ~(missing | nonnumeric | nonfinite)
    reversed_corners = (coordinates[:, 2:] < coordinates[:, :2]).any(axis=1) & finite
    zero_area = (coordinates[:, 2:] == coordinates[:, :2]).any(axis=1) & finite & ~reversed_corners
    invalid = missing | nonnumeric | nonfinite | reversed_corners | zero_area
    # Preserve upstream confidence/label/schema diagnostics before Pandera's
    # raw-evidence validation; only geometry is recoverable at this boundary.
    validation_coordinates = coordinates.copy()
    validation_coordinates[invalid] = (0.0, 0.0, 1.0, 1.0)
    validation_predictions = predictions.assign(
        **{column: validation_coordinates[:, i] for i, column in enumerate(BBOX_COLUMNS)}
    )
    validate_dataframes(validation_predictions, pd.DataFrame(columns=sorted(REQUIRED_COLS_GT)))
    validate_dataframe(predictions, "raw_predictions")
    if invalid.any():
        reasons = {
            "missing": int(missing.sum()),
            "nonnumeric": int(nonnumeric.sum()),
            "nonfinite": int(nonfinite.sum()),
            "reversed_corners": int(reversed_corners.sum()),
            "zero_area": int(zero_area.sum()),
        }
        sample = predictions.loc[invalid, "image_name"].drop_duplicates().head(5).tolist()
        logger.warning(
            "Dropped {} of {} prediction boxes with invalid geometry: {}; image sample: {}",
            int(invalid.sum()),
            len(predictions),
            ", ".join(f"{reason}={count}" for reason, count in reasons.items() if count),
            sample,
        )
    return predictions.iloc[np.flatnonzero(~invalid)].copy()


@trace_operation("evaluation.predictions.prepare")
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
    processed = preprocessor.process(assign_source_ids(predictions, row_type="prediction"))
    return cast(pd.DataFrame, processed).reset_index(drop=True)


@trace_operation("evaluation.calibration")
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
    EvaluationConfig.model_validate(
        {"iou_threshold": iou_threshold, "matching_strategy": matching_strategy}
    )
    try:
        calibration_gt = _split_ground_truth(ground_truth, calibration_split)
    except ValueError as error:
        raise ValueError(
            f"No ground-truth rows for calibration split {calibration_split!r}"
        ) from error
    validate_dataframes(predictions, calibration_gt)
    image_names = [str(value) for value in calibration_gt["image_name"].unique()]
    with trace_operation(
        "evaluation.calibration.match",
        context={"split": calibration_split, "images": len(image_names), "rows": len(predictions)},
    ):
        matches = match_boxes(
            calibration_gt,
            predictions,
            iou_threshold,
            strategy=matching_strategy,
            split_image_names=image_names,
        )
    with trace_operation("evaluation.calibration.optimize", context={"classes": len(classes)}):
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
    gt_types = outcome.gt_status.set_index("gt_index")["detected"].map({True: "TP", False: "FN"})
    pred_types = outcome.pred_status.set_index("pred_index")["is_tp"].map({True: "TP", False: "FP"})
    gt = gt_df.copy()
    gt["predict_type"] = [gt_types.get(index, "FN") for index in gt.index]
    preds = preds_df.copy()
    preds["predict_type"] = [pred_types.get(index, "filtered") for index in preds.index]
    return gt, preds


def _lineage_frames(
    ground_truth: pd.DataFrame,
    raw_predictions: pd.DataFrame,
    predictions: pd.DataFrame,
    source_ground_truth: pd.DataFrame | None,
    source_predictions: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_gt = assign_source_ids(
        ground_truth if source_ground_truth is None else source_ground_truth,
        row_type="ground_truth",
    )
    source_preds = assign_source_ids(
        raw_predictions if source_predictions is None else source_predictions,
        row_type="prediction",
    )
    if source_ground_truth is None:
        ground_truth = assign_source_ids(ground_truth, row_type="ground_truth")
    if source_predictions is None:
        predictions = assign_source_ids(predictions, row_type="prediction")
    return ground_truth, predictions, source_gt, source_preds


def _verify_pr_ap50(curves: list[PRCurve], metrics: Mapping[str, _BackendMetrics]) -> None:
    """Keep the dependency's compute_map authoritative if reconstruction drifts."""
    for curve in curves:
        if curve.gt_count == 0:
            continue
        authoritative = float(metrics[curve.class_name].ap50)
        # Both paths use the same float32 counts and public integrator. This
        # tolerance admits a float32 rounding step, not a population mismatch.
        if curve.ap50 is None or not math.isclose(
            curve.ap50,
            authoritative,
            rel_tol=1e-7,
            abs_tol=1e-9,
        ):
            raise ValueError(
                f"Reconstructed AP50 for class {curve.class_name!r} ({curve.ap50!r}) "
                f"disagrees with authoritative compute_map AP50 ({authoritative!r})"
            )


@trace_operation("evaluation.compute")
def compute_evaluation(
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
    methodology: Mapping[str, JsonValue] | None = None,
    source_ground_truth: pd.DataFrame | None = None,
    source_predictions: pd.DataFrame | None = None,
    model_identity: ModelIdentity | None = None,
) -> ComputedEvaluation:
    """Compute a split at frozen thresholds without rendering or writing outputs."""
    EvaluationConfig.model_validate(
        {
            "iou_threshold": iou_threshold,
            "matching_strategy": matching_strategy,
            "ap_method": ap_method,
        }
    )
    if not skip_cohen_kappa:
        raise ValueError("Fixed evaluation currently requires skip_cohen_kappa=True")
    required = classes if required_classes is None else required_classes
    normalized = validate_thresholds(thresholds, required)
    ground_truth, predictions, source_gt, source_preds = _lineage_frames(
        ground_truth,
        raw_predictions,
        predictions,
        source_ground_truth,
        source_predictions,
    )
    gt_df = _split_ground_truth(ground_truth, split)
    validate_dataframes(predictions, gt_df)
    gt_df = validate_dataframe(gt_df, "prepared_ground_truth")
    predictions = validate_dataframe(predictions, "evaluation_predictions")
    raw_predictions = validate_dataframe(raw_predictions, "evaluation_predictions")
    image_names = [str(value) for value in gt_df["image_name"].unique()]
    with trace_operation(
        "evaluation.match",
        context={"split": split, "images": len(image_names), "rows": len(predictions)},
    ):
        matches = match_boxes(
            gt_df,
            predictions,
            iou_threshold,
            strategy=matching_strategy,
            split_image_names=image_names,
        )
    sliced = cast(dict[str, list[MatchRecord]], slice_by_conf(matches, classes, normalized))
    payload_methodology: dict[str, JsonValue] = {
        "iou_threshold": iou_threshold,
        "matching_strategy": matching_strategy,
        "ap_method": ap_method,
        "skip_cohen_kappa": skip_cohen_kappa,
    }
    if methodology is not None:
        payload_methodology.update(methodology)
    evaluation_payload = build_evaluation_payload(
        gt_df,
        predictions,
        split=split,
        image_names=image_names,
        thresholds=normalized,
        sliced=sliced,
        methodology=payload_methodology,
        model_identity=model_identity,
    )
    with trace_operation("evaluation.metrics", context={"split": split, "classes": len(classes)}):
        metrics = cast(
            dict[str, _BackendMetrics], compute_metrics_from_matches(sliced, classes, normalized)
        )
    # Preserve authoritative AP inputs: prepared GT and geometry-valid predictions
    # before optional confidence filtering/NMS. Raw source rows are export evidence.
    gt_boxes = gt_df.dropna(subset=BBOX_COLUMNS)
    with trace_operation(
        "evaluation.ap",
        context={"split": split, "images": len(image_names), "classes": len(classes)},
    ):
        compute_map(
            gt_boxes,
            raw_predictions,
            metrics,
            image_names,
            method=ap_method,
            strategy=matching_strategy,
        )
    cm, class_labels = get_confusion_matrix(sliced, classes)
    confusion_matrix = ConfusionMatrixPayload(labels=class_labels, counts=cm.tolist())
    with trace_operation("evaluation.pr", context={"split": split, "classes": len(classes)}):
        pr_curves = build_pr_curves(
            gt_boxes,
            raw_predictions,
            classes=classes,
            image_names=image_names,
            matching_strategy=matching_strategy,
            ap_method=ap_method,
        )
    _verify_pr_ap50(pr_curves, metrics)
    evaluation_payload.report = EvaluationReport(
        classes=list(classes),
        confusion_matrix=confusion_matrix,
        pr_curves=pr_curves,
        average_precisions={
            curve.class_name: ClassAveragePrecision(
                ap50=float(metrics[curve.class_name].ap50) if curve.gt_count else None,
                ap75=float(metrics[curve.class_name].ap75) if curve.gt_count else None,
                ap50_95=float(metrics[curve.class_name].ap50_95) if curve.gt_count else None,
            )
            for curve in pr_curves
        },
    )
    with trace_operation("evaluation.result_rows", context={"split": split}):
        result_rows = build_result_rows(
            source_gt,
            source_preds,
            prepared_ground_truth=gt_df,
            prepared_predictions=predictions,
            split=split,
            thresholds=normalized,
            matches_pre_threshold=_match_values(matches),
            matches_post_threshold=_match_values(sliced),
        )
    outcome = _outcome_from_matches(gt_df, predictions, classes, sliced)

    gt_matches, pred_matches = _visualization_frames(gt_df, predictions, outcome)
    return ComputedEvaluation(
        split=split,
        image_names=image_names,
        thresholds=normalized,
        metrics={name: _metric_values(metric) for name, metric in metrics.items()},
        outcome=outcome,
        ground_truth=ground_truth,
        gt_matches=gt_matches,
        pred_matches=pred_matches,
        evaluation_payload=evaluation_payload,
        confusion_matrix=confusion_matrix,
        pr_curves=pr_curves,
        result_rows=result_rows,
        model_identity=model_identity,
    )


def _match_values(matches: Mapping[str, list[MatchRecord]]) -> dict[str, list[MatchResult]]:
    """Keep the dependency's objects inside this adapter at the core boundary."""
    return {
        name: [
            MatchResult(
                type=match.type,
                gt_index=match.gt_index,
                pred_index=match.pred_index,
                gt_label=match.gt_label,
                pred_label=match.pred_label,
                confidence=match.confidence,
                iou=match.iou,
            )
            for match in records
        ]
        for name, records in matches.items()
    }


def _metric_values(metric: _BackendMetrics) -> DetectionMetrics:
    """Copy explicit backend fields after all authoritative computations finish."""
    return DetectionMetrics(
        counts_observed=metric.counts_observed,
        tp=metric.tp,
        fp=metric.fp,
        fn=metric.fn,
        confidence=metric.confidence,
        ap50=metric.ap50,
        ap75=metric.ap75,
        ap50_95=metric.ap50_95,
        cohen_kappa=metric.cohen_kappa,
        precision=metric.precision,
        recall=metric.recall,
        f1_score=metric.f1_score,
        perebrak=metric.perebrak,
        nedobrak=metric.nedobrak,
        precision_ci_lower=metric.precision_ci_lower,
        precision_ci_upper=metric.precision_ci_upper,
        recall_ci_lower=metric.recall_ci_lower,
        recall_ci_upper=metric.recall_ci_upper,
        perebrak_ci_lower=metric.perebrak_ci_lower,
        perebrak_ci_upper=metric.perebrak_ci_upper,
        nedobrak_ci_lower=metric.nedobrak_ci_lower,
        nedobrak_ci_upper=metric.nedobrak_ci_upper,
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

    ``gt_status`` is built from every scored ground-truth row to preserve the
    recall denominator. Upstream assignment is class-aware for every strategy:
    a cross-class prediction leaves the ground-truth box unmatched and records
    its FN, so ``len(gt_status)`` equals ``tp + fn``.

    Only a class's own TP record marks a ground-truth box detected. A cross-class
    false positive also carries a ``gt_index``, but that box's real status is
    recorded by its own TP or FN record.
    """
    EvaluationConfig.model_validate(
        {"iou_threshold": iou_threshold, "matching_strategy": matching_strategy}
    )
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
