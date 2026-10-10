"""Reconstruct the pinned dependency's AP50 curve using its public kernels."""

import numpy as np
import pandas as pd
from digital_metrics.matching import (
    assign_greedy,
    assign_hungarian,
    assign_iou_prior,
    compute_iou_matrix,
)
from digital_metrics.scoring import compute_ap
from digital_metrics.validation import normalize_image_ids, validate_dataframes, validate_option
from numpy.typing import NDArray

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core.evaluation.schema import PRCurve

_BOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


def _true_positive_flags(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    strategy: str,
) -> NDArray[np.float32]:
    """Assign per image with the float32 boxes used by authoritative compute_map."""
    pred_boxes = predictions[_BOX_COLUMNS].to_numpy(np.float32)
    gt_boxes = truth[_BOX_COLUMNS].to_numpy(np.float32)
    gt_by_image = {
        str(image): gt_boxes[positions]
        for image, positions in truth.groupby("image_name").indices.items()
    }
    assignment = {
        "greedy": assign_greedy,
        "hungarian": assign_hungarian,
        "iou_prior": assign_iou_prior,
    }[strategy]
    tp = np.zeros(len(predictions), dtype=np.float32)
    for image, positions in predictions.groupby("image_name", sort=False).indices.items():
        gt = gt_by_image.get(str(image))
        if gt is None or gt.size == 0:
            continue
        pairs = assignment(compute_iou_matrix(pred_boxes[positions], gt), 0.5)
        for local_pred, _ in pairs:
            tp[positions[local_pred]] = 1.0
    return tp


@trace_operation("evaluation.pr.curves")
def build_pr_curves(
    ground_truth: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    classes: list[str],
    image_names: list[str],
    matching_strategy: str,
    ap_method: str,
) -> list[PRCurve]:
    """Return AP-population curves, without a fixed-threshold operating point.

    The default pandas confidence sort, float32 cumulative arithmetic and epsilon
    deliberately match compute_map, including tied confidences. No-GT classes
    carry no observations because their recall is unavailable.
    """
    validate_option("ap_method", ap_method, ("interp", "continuous"))
    validate_option("matching_strategy", matching_strategy, ("greedy", "hungarian", "iou_prior"))
    validate_dataframes(predictions, ground_truth)
    truth, preds, scope = normalize_image_ids(
        ground_truth,
        predictions,
        pd.DataFrame({"image_name": image_names}),
    )
    truth = truth[truth["image_name"].isin(scope["image_name"])]
    preds = preds[preds["image_name"].isin(scope["image_name"])]
    curves: list[PRCurve] = []
    for class_name in classes:
        class_truth = truth[truth["instance_label"] == class_name]
        class_preds = preds[preds["instance_label"] == class_name].sort_values(
            by="confidence",
            ascending=False,
        )
        gt_count = len(class_truth)
        if gt_count == 0:
            curves.append(
                PRCurve(
                    class_name=class_name,
                    recall=[],
                    precision=[],
                    confidence=[],
                    tp=[],
                    fp=[],
                    gt_count=0,
                    ap50=None,
                    integration_method=ap_method,
                )
            )
            continue
        tp = _true_positive_flags(class_truth, class_preds, matching_strategy)
        tp_cum = np.cumsum(tp)
        fp_cum = np.cumsum(np.ones(len(tp), dtype=np.float32) - tp)
        recall = tp_cum / max(gt_count, 1)
        precision = tp_cum / (tp_cum + fp_cum + 1e-12)
        curves.append(
            PRCurve(
                class_name=class_name,
                recall=recall.tolist(),
                precision=precision.tolist(),
                confidence=class_preds["confidence"].astype(float).tolist(),
                tp=tp_cum.astype(int).tolist(),
                fp=fp_cum.astype(int).tolist(),
                gt_count=gt_count,
                ap50=float(compute_ap(recall, precision, ap_method)),
                integration_method=ap_method,
            )
        )
    return curves
