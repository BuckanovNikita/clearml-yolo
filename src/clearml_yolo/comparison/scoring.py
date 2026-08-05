"""Score one split at fixed per-class confidence thresholds.

digital-metrics exposes no public way to score at thresholds that were solved
elsewhere: ``Evaluation`` either calibrates in-sample or on a held-out split, and
its threshold search is private. Comparing two models fairly needs the opposite —
the same split scored twice at each model's own frozen production thresholds — so
this module composes the public sub-package functions (``match_boxes`` then
``slice_by_conf``) and does its own tally.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from digital_metrics.matching import match_boxes
from digital_metrics.scoring import slice_by_conf
from loguru import logger
from pydantic import BaseModel

BBOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


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
    if not gt_df.index.is_unique:
        raise ValueError("Ground-truth index has duplicate labels, so match records cannot join.")
    if not preds_df.index.is_unique:
        raise ValueError("Prediction index has duplicate labels, so match records cannot join.")

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
    sliced = slice_by_conf(matches, classes, thresholds)

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
    unknown_labels = sorted(set(scored_gt["instance_label"]) - set(classes))
    if unknown_labels:
        logger.warning(
            "Ground truth carries label(s) {} outside the scored classes {}; "
            "those boxes are excluded from the outcome.",
            unknown_labels,
            classes,
        )
    scored_gt = scored_gt[scored_gt["instance_label"].isin(classes)]

    gt_status = pd.DataFrame(
        {
            "gt_index": scored_gt.index.to_numpy(),
            "image_name": scored_gt["image_name"].to_numpy(),
            "instance_label": scored_gt["instance_label"].to_numpy(),
            "detected": scored_gt.index.isin(sorted(detected_gt_indices)),
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

    logger.debug(
        "Scored {} ground-truth boxes and {} surviving predictions over {} classes",
        len(gt_status),
        len(pred_status),
        len(classes),
    )
    return SplitOutcome(counts=counts, gt_status=gt_status, pred_status=pred_status)
