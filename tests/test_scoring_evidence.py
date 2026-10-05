"""Evaluation payloads and CSV lineage share the real fixed-score results."""

import json
from pathlib import Path

import pandas as pd
import pytest
from digital_metrics.matching import match_boxes
from digital_metrics.scoring import compute_map, get_confusion_matrix, slice_by_conf
from digital_metrics.types import Metrics

from clearml_yolo.comparison.scoring import (
    evaluate_split,
    filter_invalid_prediction_boxes,
    prepare_ground_truth,
    prepare_predictions,
)
from clearml_yolo.result_export import assign_source_ids, prepared_source_mapping
from clearml_yolo.result_schema import PRCurve

COLUMNS = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


def test_evaluation_keeps_raw_ap_and_prepared_fixed_match_populations_separate(
    tmp_path: Path,
) -> None:
    gt = assign_source_ids(pd.DataFrame([
        ("a", "42", 0, 0, 10, 10), ("a", "42", 0, 0, 10, 10),
        ("b", "42", 0, 0, 10, 10), ("empty", None, None, None, None, None),
    ], columns=COLUMNS).assign(split="test", original="retained"), row_type="ground_truth")
    preds = assign_source_ids(pd.DataFrame([
        ("a", "42", 0, 0, 10, 10, 0.9), ("a", "42", 0, 0, 10, 10, 0.8),
        ("b", "42", 0, 0, 10, 10, 0.1), ("empty", "42", 0, 0, 10, 10, 0.7),
        ("a", "42", 0, 0, 0, 10, 0.9),
    ], columns=[*COLUMNS, "confidence"]), row_type="prediction")
    truth = prepare_ground_truth(gt, deduplicate=True)
    raw = filter_invalid_prediction_boxes(preds)
    prepared = prepare_predictions(raw, preprocess_conf_threshold=0.2,
                                   preprocess_nms_containment_threshold=0.5,
                                   preprocess_nms_iou_threshold=None)
    evaluated = evaluate_split(
        truth, raw, prepared, split="test", classes=["42"], thresholds={"42": 0.7},
        required_classes=["42"], iou_threshold=0.5, matching_strategy="iou_prior",
        ap_method="interp", skip_cohen_kappa=True, output_dir=tmp_path, suffix="test",
        source_ground_truth=gt, source_predictions=preds,
    )
    assert evaluated.outcome.counts["42"].model_dump() == {"tp": 1, "fp": 1, "fn": 1}
    assert evaluated.confusion_matrix.labels == ["42", "background"]
    assert evaluated.confusion_matrix.counts == [[1, 1], [1, 0]]
    assert len(evaluated.result_rows) == 9
    curve = evaluated.pr_curves[0]
    assert curve.gt_count == 2  # Prepared GT controls authoritative AP; duplicate is export only.
    assert curve.confidence == [0.9, 0.8, 0.7, 0.1]  # NMS/filtering do not change AP population.
    authoritative = {"42": Metrics()}
    compute_map(truth.dropna(subset=COLUMNS[2:]), raw, authoritative,
                ["a", "b", "empty"], method="interp", strategy="iou_prior")
    assert curve.ap50 == authoritative["42"].ap50 == evaluated.metrics["42"].ap50
    before = match_boxes(truth, prepared, 0.5, strategy="iou_prior",
                         split_image_names=["a", "b", "empty"])
    after = slice_by_conf(before, ["42"], {"42": 0.7})
    matrix, labels = get_confusion_matrix(after, ["42"])
    assert evaluated.confusion_matrix.counts == matrix.tolist()
    assert evaluated.confusion_matrix.labels == labels
    rows = evaluated.result_rows.set_index("source_row_id")
    assert rows.loc["gt:1", "exclusion_reason"] == "duplicate_ground_truth"
    assert rows.loc["pred:1", "exclusion_reason"] == "prediction_preprocessing"
    assert rows.loc["pred:2", "exclusion_reason"] == "prediction_preprocessing"
    assert rows.loc["pred:4", "exclusion_reason"] == "invalid_geometry:zero_area"
    assert not rows.loc["pred:3", "is_below_threshold"]  # Equal threshold is kept.
    for source_id in ("pred:0", "pred:3"):
        relations = json.loads(str(rows.loc[source_id, "matches_post_threshold"]))
        assert len(relations) == 1
        assert relations[0]["pred_source_row_id"] == source_id
        assert relations[0]["pred_index"] == rows.loc[source_id, "prepared_index"]


@pytest.mark.parametrize("empty_predictions", [False, True])
def test_background_only_split_retains_rows_and_unavailable_ap(
    tmp_path: Path, empty_predictions: bool,
) -> None:
    gt = assign_source_ids(pd.DataFrame([
        ("empty", None, None, None, None, None),
    ], columns=COLUMNS).assign(split="test"), row_type="ground_truth")
    preds = assign_source_ids(pd.DataFrame([
        ("empty", "кошка", 0, 0, 10, 10, 0.7),
    ], columns=[*COLUMNS, "confidence"]), row_type="prediction")
    if empty_predictions:
        preds = preds.iloc[:0]
    prepared = prepare_predictions(preds, preprocess_conf_threshold=None,
                                   preprocess_nms_containment_threshold=None,
                                   preprocess_nms_iou_threshold=None)
    evaluated = evaluate_split(
        prepare_ground_truth(gt, deduplicate=False), preds, prepared, split="test",
        classes=["кошка"], thresholds={"кошка": 0.7}, required_classes=["кошка"],
        iou_threshold=0.5, matching_strategy="greedy", ap_method="continuous",
        skip_cohen_kappa=True, output_dir=tmp_path, suffix="test",
        source_ground_truth=gt, source_predictions=preds,
    )
    assert evaluated.confusion_matrix.counts == [[0, 0], [int(not empty_predictions), 0]]
    assert evaluated.pr_curves[0].ap50 is None
    assert evaluated.pr_curves[0].recall == []
    assert len(evaluated.result_rows) == (1 if empty_predictions else 2)
    assert evaluated.result_rows.iloc[0].evaluation_status == "background"


def test_prepared_mapping_rejects_missing_and_unknown_lineage() -> None:
    source = assign_source_ids(pd.DataFrame([("a", "42", 0, 0, 10, 10)], columns=COLUMNS),
                               row_type="ground_truth")
    with pytest.raises(ValueError, match="explicit"):
        prepared_source_mapping(source.drop(columns="source_row_id"), source)
    with pytest.raises(ValueError, match="absent"):
        prepared_source_mapping(source.assign(source_row_id="invented"), source)


def test_evaluation_fails_when_reconstructed_ap50_disagrees_with_authoritative_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    gt = prepare_ground_truth(pd.DataFrame([
        ("a", "42", 0, 0, 10, 10),
    ], columns=COLUMNS).assign(split="test"), deduplicate=False)
    preds = assign_source_ids(pd.DataFrame([
        ("a", "42", 0, 0, 10, 10, 0.9),
    ], columns=[*COLUMNS, "confidence"]), row_type="prediction")
    mismatched_curve = PRCurve(
        class_name="42", recall=[1.0], precision=[1.0], confidence=[0.9],
        tp=[1], fp=[0], gt_count=1, ap50=0.25, integration_method="interp",
    )
    monkeypatch.setattr("clearml_yolo.comparison.scoring.build_pr_curves",
                        lambda *args, **kwargs: [mismatched_curve])
    with pytest.raises(ValueError, match=r"Reconstructed AP50.*42.*authoritative"):
        evaluate_split(
            gt, preds, preds, split="test", classes=["42"], thresholds={"42": 0.7},
            required_classes=["42"], iou_threshold=0.5, matching_strategy="iou_prior",
            ap_method="interp", skip_cohen_kappa=True, output_dir=tmp_path, suffix="test",
        )
    assert list(tmp_path.iterdir()) == []
