"""Fixed-threshold scoring must tally exactly what the match records describe."""

from __future__ import annotations

import pandas as pd
import pytest

from clearml_yolo.comparison.scoring import ClassCounts, score_split

GT_COLUMNS = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
GtRow = tuple[str, str | None, float, float, float, float]
PredRow = tuple[str, str, float, float, float, float, float]


def _gt_frame(rows: list[GtRow], index: list[int]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=GT_COLUMNS, index=pd.Index(index))
    frame["split"] = "test"
    return frame


def _pred_frame(rows: list[PredRow], index: list[int]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=[*GT_COLUMNS, "confidence"], index=pd.Index(index))


def test_hits_and_background_false_positive_join_back_by_index_label() -> None:
    gt = _gt_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
            ("img2.jpg", "dog", 20.0, 20.0, 30.0, 30.0),
        ],
        index=[100, 101],
    )
    preds = _pred_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9),
            ("img2.jpg", "dog", 20.0, 20.0, 30.0, 30.0, 0.8),
            ("img1.jpg", "dog", 50.0, 50.0, 60.0, 60.0, 0.7),
        ],
        index=[7, 8, 9],
    )

    outcome = score_split(
        gt,
        preds,
        ["cat", "dog"],
        {"cat": 0.5, "dog": 0.5},
        iou_threshold=0.5,
        matching_strategy="iou_prior",
    )

    assert outcome.counts == {
        "cat": ClassCounts(tp=1, fp=0, fn=0),
        "dog": ClassCounts(tp=1, fp=1, fn=0),
    }
    assert len(outcome.gt_status) == sum(tally.tp + tally.fn for tally in outcome.counts.values())
    assert outcome.gt_status["gt_index"].tolist() == [100, 101]
    assert outcome.gt_status["image_name"].tolist() == ["img1.jpg", "img2.jpg"]
    assert outcome.gt_status["detected"].tolist() == [True, True]
    assert outcome.pred_status["pred_index"].tolist() == [7, 8, 9]
    assert outcome.pred_status["image_name"].tolist() == ["img1.jpg", "img2.jpg", "img1.jpg"]
    assert outcome.pred_status["instance_label"].tolist() == ["cat", "dog", "dog"]
    assert outcome.pred_status["is_tp"].tolist() == [True, True, False]


def _two_cats_one_weak() -> tuple[pd.DataFrame, pd.DataFrame]:
    gt = _gt_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
            ("img2.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
        ],
        index=[0, 1],
    )
    preds = _pred_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9),
            ("img2.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.3),
        ],
        index=[5, 6],
    )
    return gt, preds


def test_prediction_below_its_class_threshold_becomes_a_miss() -> None:
    gt, preds = _two_cats_one_weak()

    outcome = score_split(
        gt, preds, ["cat"], {"cat": 0.5}, iou_threshold=0.5, matching_strategy="iou_prior"
    )

    assert outcome.counts == {"cat": ClassCounts(tp=1, fp=0, fn=1)}
    assert outcome.gt_status["detected"].tolist() == [True, False]
    assert outcome.pred_status["pred_index"].tolist() == [5]


def test_class_missing_from_thresholds_is_scored_at_zero() -> None:
    gt, preds = _two_cats_one_weak()

    outcome = score_split(gt, preds, ["cat"], {}, iou_threshold=0.5, matching_strategy="iou_prior")

    assert outcome.counts == {"cat": ClassCounts(tp=2, fp=0, fn=0)}
    assert outcome.gt_status["detected"].tolist() == [True, True]
    assert outcome.pred_status["pred_index"].tolist() == [5, 6]


def test_empty_predictions_leave_every_ground_truth_box_undetected() -> None:
    gt, _ = _two_cats_one_weak()

    outcome = score_split(
        gt,
        _pred_frame([], []),
        ["cat", "dog"],
        {"cat": 0.5, "dog": 0.5},
        iou_threshold=0.5,
        matching_strategy="iou_prior",
    )

    assert outcome.counts == {
        "cat": ClassCounts(tp=0, fp=0, fn=2),
        "dog": ClassCounts(tp=0, fp=0, fn=0),
    }
    assert outcome.gt_status["gt_index"].tolist() == [0, 1]
    assert outcome.gt_status["detected"].tolist() == [False, False]
    assert outcome.pred_status.empty
    assert list(outcome.pred_status.columns) == [
        "pred_index",
        "image_name",
        "instance_label",
        "is_tp",
    ]


def _one_gt_one_cross_class_prediction() -> tuple[pd.DataFrame, pd.DataFrame]:
    gt = _gt_frame([("img1.jpg", "dog", 0.0, 0.0, 10.0, 10.0)], index=[42])
    preds = _pred_frame([("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9)], index=[3])
    return gt, preds


def test_greedy_cross_class_match_still_lists_the_consumed_ground_truth_box() -> None:
    """Greedy assignment is label-agnostic, so the GT box is consumed by a foreign
    class and yields no match record at all — only the every-GT-row pass keeps it."""
    gt, preds = _one_gt_one_cross_class_prediction()

    outcome = score_split(
        gt,
        preds,
        ["cat", "dog"],
        {"cat": 0.5, "dog": 0.5},
        iou_threshold=0.5,
        matching_strategy="greedy",
    )

    assert outcome.counts == {
        "cat": ClassCounts(tp=0, fp=1, fn=0),
        "dog": ClassCounts(tp=0, fp=0, fn=0),
    }
    assert outcome.gt_status["gt_index"].tolist() == [42]
    assert outcome.gt_status["detected"].tolist() == [False]


def test_cross_class_false_positive_does_not_mark_its_ground_truth_detected() -> None:
    gt, preds = _one_gt_one_cross_class_prediction()

    outcome = score_split(
        gt,
        preds,
        ["cat", "dog"],
        {"cat": 0.5, "dog": 0.5},
        iou_threshold=0.5,
        matching_strategy="iou_prior",
    )

    assert outcome.counts == {
        "cat": ClassCounts(tp=0, fp=1, fn=0),
        "dog": ClassCounts(tp=0, fp=0, fn=1),
    }
    assert outcome.gt_status["detected"].tolist() == [False]
    assert outcome.pred_status["pred_index"].tolist() == [3]
    assert outcome.pred_status["is_tp"].tolist() == [False]


@pytest.mark.parametrize(
    ("index", "message"),
    [([0, 0], "duplicate labels"), ([-1, 1], "negative labels")],
)
def test_indexes_that_cannot_carry_the_join_are_rejected(index: list[int], message: str) -> None:
    gt = _gt_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
            ("img2.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
        ],
        index=index,
    )

    with pytest.raises(ValueError, match=message):
        score_split(
            gt,
            _pred_frame([], []),
            ["cat"],
            {"cat": 0.5},
            iou_threshold=0.5,
            matching_strategy="iou_prior",
        )


def test_labels_outside_the_scored_classes_are_excluded_without_crashing() -> None:
    gt = _gt_frame(
        [
            ("img1.jpg", "cat", 0.0, 0.0, 10.0, 10.0),
            ("img2.jpg", "bird", 20.0, 20.0, 30.0, 30.0),
            ("img3.jpg", None, 40.0, 40.0, 50.0, 50.0),
        ],
        index=[0, 1, 2],
    )

    outcome = score_split(
        gt, _pred_frame([], []), ["cat"], {}, iou_threshold=0.5, matching_strategy="iou_prior"
    )

    assert outcome.counts == {"cat": ClassCounts(tp=0, fp=0, fn=1)}
    assert outcome.gt_status["gt_index"].tolist() == [0]
