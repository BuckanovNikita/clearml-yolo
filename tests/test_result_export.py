"""Source lineage preserves rows that disappear during scoring preparation."""

import json

import pandas as pd
import pytest
from digital_metrics.matching import match_boxes
from digital_metrics.scoring import slice_by_conf

from clearml_yolo.comparison.scoring import prepare_ground_truth, prepare_predictions
from clearml_yolo.result_export import (
    assign_source_ids,
    build_ground_truth_rows,
    build_prediction_rows,
    build_result_rows,
)

COLUMNS = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


def test_stable_ids_distinguish_identical_rows_and_survive_deduplication() -> None:
    raw = pd.DataFrame([("a", "cat", 0, 0, 10, 10)] * 2, columns=COLUMNS,
                       index=[5, 5]).assign(split="test")
    source = assign_source_ids(raw, row_type="ground_truth")
    prepared = prepare_ground_truth(source, deduplicate=True)
    assert source.source_row_id.nunique() == 2
    assert len(prepared) == 1
    assert prepared.source_row_id.tolist() == source.iloc[[0]].source_row_id.tolist()
    assert "source_row_id" not in raw
    pd.testing.assert_frame_equal(assign_source_ids(source, row_type="ground_truth"), source)


def test_export_records_all_relationships_and_excluded_source_rows() -> None:
    gt = assign_source_ids(pd.DataFrame([
        ("a", "cat", 0, 0, 10, 10), ("a", "cat", 0, 0, 10, 10),
        ("b", None, None, None, None, None),
    ], columns=COLUMNS).assign(split="test"), row_type="ground_truth")
    preds = assign_source_ids(pd.DataFrame([
        ("a", "cat", 0, 0, 10, 10, 0.5), ("a", "dog", 0, 0, 10, 10, 0.9),
        ("b", "cat", 0, 0, 10, 10, 0.5), ("a", "cat", 0, 0, 0, 10, 0.9),
        ("a", "cat", 30, 0, 40, 10, 0.1),
    ], columns=[*COLUMNS, "confidence"]), row_type="prediction")
    prepared_gt = prepare_ground_truth(gt, deduplicate=True)
    prepared_preds = prepare_predictions(preds.iloc[[0, 1, 2, 4]], preprocess_conf_threshold=0.2,
                                        preprocess_nms_containment_threshold=None,
                                        preprocess_nms_iou_threshold=None)
    before = match_boxes(prepared_gt, prepared_preds, 0.5, strategy="iou_prior",
                         split_image_names=["a", "b"])
    after = slice_by_conf(before, ["cat", "dog"], {"cat": 0.6, "dog": 0.9})
    rows = build_result_rows(gt, preds, prepared_ground_truth=prepared_gt,
                             prepared_predictions=prepared_preds, split="test",
                             thresholds={"cat": 0.6, "dog": 0.9},
                             matches_pre_threshold=before, matches_post_threshold=after)
    assert len(rows) == len(gt) + len(preds)
    gt_rows = rows[rows.row_type == "gt"].set_index("source_row_id")
    pred_rows = rows[rows.row_type == "predict"].set_index("source_row_id")
    assert gt_rows.loc["gt:1", "exclusion_reason"] == "duplicate_ground_truth"
    assert gt_rows.loc["gt:2", "evaluation_status"] == "background"
    assert pred_rows.loc["pred:3", "exclusion_reason"] == "invalid_geometry:zero_area"
    assert pred_rows.loc["pred:4", "exclusion_reason"] == "prediction_preprocessing"
    assert pred_rows.loc["pred:0", "is_below_threshold"]
    assert not pred_rows.loc["pred:1", "is_below_threshold"]
    assert all(pd.isna(value) for value in gt_rows.is_below_threshold)
    relationships = json.loads(str(gt_rows.loc["gt:0", "matches_pre_threshold"]))
    assert {relation["pred_source_row_id"] for relation in relationships} == {"pred:0", "pred:1"}
    assert json.loads(str(pred_rows.loc["pred:0", "matches_post_threshold"])) == []
    post = json.loads(str(gt_rows.loc["gt:0", "matches_post_threshold"]))
    assert {relationship["status"] for relationship in post} == {"FP", "FN"}
    for relationship in relationships:
        pred = pred_rows.loc[relationship["pred_source_row_id"]]
        assert relationship in json.loads(pred.matches_pre_threshold)


def test_unevaluated_exports_retain_original_fields_and_null_threshold_flags() -> None:
    frame = pd.DataFrame([("a", "cat", 0, 0, 10, 10, 0.5)],
                         columns=[*COLUMNS, "confidence"]).assign(extra="original")
    rows = build_prediction_rows(frame, split="val")
    assert rows.iloc[0].evaluation_status == "not_evaluated"
    assert rows.iloc[0].extra == "original"
    assert pd.isna(rows.iloc[0].is_below_threshold)
    truth = build_ground_truth_rows(frame.drop(columns="confidence"))
    assert truth.iloc[0].row_type == "gt"


def test_source_ids_must_be_unique_and_prepared_mappings_must_be_explicit() -> None:
    frame = pd.DataFrame([("a", "cat", 0, 0, 10, 10)] * 2, columns=COLUMNS)
    with pytest.raises(ValueError, match="unique"):
        assign_source_ids(frame.assign(source_row_id="same"), row_type="ground_truth")


def test_relationships_namespace_explicit_source_ids_by_row_type() -> None:
    gt = pd.DataFrame([("a", "cat", 0, 0, 10, 10)], columns=COLUMNS).assign(
        split="test", source_row_id="1",
    )
    preds = pd.DataFrame([("a", "cat", 20, 0, 30, 10, 0.9)],
                         columns=[*COLUMNS, "confidence"]).assign(source_row_id="1")
    before = match_boxes(gt, preds, 0.5, strategy="greedy", split_image_names=["a"])
    after = slice_by_conf(before, ["cat"], {"cat": 0.5})
    rows = build_result_rows(gt, preds, prepared_ground_truth=gt, prepared_predictions=preds,
                             split="test", thresholds={"cat": 0.5},
                             matches_pre_threshold=before, matches_post_threshold=after)
    truth, prediction = rows.iloc[0], rows.iloc[1]
    assert truth.evaluation_status == "FN"
    assert prediction.evaluation_status == "FP"
    gt_relations = json.loads(truth.matches_post_threshold)
    pred_relations = json.loads(prediction.matches_post_threshold)
    assert len(gt_relations) == len(pred_relations) == 1
    assert gt_relations[0]["pred_source_row_id"] is None
    assert pred_relations[0]["gt_source_row_id"] is None
