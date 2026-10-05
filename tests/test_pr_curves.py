"""PR reconstruction must agree with the pinned public AP implementation."""

import math

import pandas as pd
import pytest
from digital_metrics.scoring import compute_map
from digital_metrics.types import Metrics

from clearml_yolo.comparison.pr_curves import build_pr_curves

COLUMNS = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


@pytest.mark.parametrize("strategy", ["greedy", "hungarian", "iou_prior"])
@pytest.mark.parametrize("method", ["interp", "continuous"])
@pytest.mark.parametrize("empty", [False, True])
def test_pr_ap50_matches_authoritative_population_order_and_arithmetic(
    strategy: str, method: str, empty: bool,
) -> None:
    gt = pd.DataFrame([
        ("1", "кошка", 0, 0, 10, 10), ("1", "кошка", 7, 0, 17, 10),
        ("2", "кошка", 0, 0, 10, 10), ("3", None, None, None, None, None),
    ], columns=COLUMNS)
    predictions = pd.DataFrame([
        ("1", "кошка", 2, 0, 12, 10, 0.9), ("1", "кошка", 0, 0, 10, 10, 0.8),
        ("1", "кошка", 7, 0, 17, 10, 0.8), ("3", "кошка", 0, 0, 10, 10, 0.8),
        ("2", "кошка", 0, 0, 10, 10, 0.5), ("9", "кошка", 0, 0, 10, 10, 1.0),
    ], columns=[*COLUMNS, "confidence"])
    if empty:
        predictions = predictions.iloc[:0]
    metrics = {"кошка": Metrics(), "42": Metrics()}
    boxes = gt.dropna(subset=COLUMNS[2:])
    compute_map(boxes, predictions, metrics, ["1", "2", "3"], method=method, strategy=strategy)
    curves = build_pr_curves(boxes, predictions, classes=["кошка", "42"],
                            image_names=["1", "2", "3"], matching_strategy=strategy,
                            ap_method=method)
    assert curves[0].ap50 == metrics["кошка"].ap50
    assert curves[0].gt_count == 3
    assert curves[0].confidence == ([] if empty else [0.9, 0.8, 0.8, 0.8, 0.5])
    assert curves[1].ap50 is None
    assert math.isnan(metrics["42"].ap50)
    assert curves[1].recall == curves[1].precision == curves[1].confidence == []


def test_prediction_only_class_has_unavailable_recall() -> None:
    gt = pd.DataFrame(columns=COLUMNS)
    predictions = pd.DataFrame([("1", "42", 0, 0, 10, 10, 0.7)],
                               columns=[*COLUMNS, "confidence"])
    curve = build_pr_curves(gt, predictions, classes=["42"], image_names=["1"],
                           matching_strategy="greedy", ap_method="continuous")[0]
    assert curve.ap50 is None
    assert curve.gt_count == 0
    assert curve.recall == curve.precision == curve.confidence == curve.tp == curve.fp == []
