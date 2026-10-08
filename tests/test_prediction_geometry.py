"""Malformed prediction geometry is excluded before preprocessing and raw AP."""

import pandas as pd
import pytest
from loguru import logger

from clearml_yolo.adapters.evaluation.scoring import calibrate_thresholds
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.metrics import EvaluationConfig, _prepare
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414

COLUMNS = [
    "image_name",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "confidence",
]


def _truth() -> pd.DataFrame:
    return pd.DataFrame(
        [("valid.jpg", "cat", 0, 0, 10, 10, "val")],
        columns=[*COLUMNS[:-1], "split"],
    )


@pytest.mark.parametrize("preprocess", [False, True])
def test_geometry_filter_keeps_valid_predictions_and_reports_reasons(
    preprocess: bool, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame(
        [
            ("zero.jpg", "cat", 0, 0, 0, 10, 0.9),
            ("valid.jpg", "cat", 0, 0, 10, 10, 0.8),
            ("reverse.jpg", "cat", 5, 0, 1, 10, 0.9),
            ("missing.jpg", "cat", None, 0, 10, 10, 0.9),
            ("text.jpg", "cat", "bad", 0, 10, 10, 0.9),
            ("infinite.jpg", "cat", 0, 0, float("inf"), 10, 0.9),
            ("low.jpg", "cat", 20, 20, 30, 30, 0.1),
        ],
        columns=COLUMNS,
    )
    original = predictions.copy(deep=True)
    warnings: list[str] = []
    sink = logger.add(lambda message: warnings.append(str(message)), level="WARNING")
    config = EvaluationConfig(
        preprocess_preds_conf_threshold=0.5 if preprocess else None,
        preprocess_preds_nms_containment_threshold=0.9 if preprocess else None,
        preprocess_preds_nms_iou_threshold=0.9 if preprocess else None,
    )
    try:
        _, raw, prepared, classes = _prepare(
            predictions, _truth(), config, deps=workflow_dependencies
        )
    finally:
        logger.remove(sink)

    pd.testing.assert_frame_equal(predictions, original)
    assert raw.image_name.tolist() == ["valid.jpg", "low.jpg"]
    assert prepared.image_name.tolist() == (
        ["valid.jpg"] if preprocess else ["valid.jpg", "low.jpg"]
    )
    assert classes == ["cat"]
    assert len(warnings) == 1
    assert "5 of 7" in warnings[0]
    for reason in ("zero_area=1", "reversed_corners=1", "missing=1", "nonnumeric=1", "nonfinite=1"):
        assert reason in warnings[0]
    for name in ("zero.jpg", "reverse.jpg", "missing.jpg", "text.jpg", "infinite.jpg"):
        assert name in warnings[0]


@pytest.mark.parametrize("column", COLUMNS[2:6])
@pytest.mark.parametrize("value", [None, pd.NA, float("nan"), float("inf"), -float("inf"), "bad"])
def test_invalid_coordinate_cells_leave_empty_predictions(
    column: str, value: object, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame(
        [("valid.jpg", "cat", 0, 0, 10, 10, 0.8)],
        columns=COLUMNS,
    ).astype({column: object})
    predictions[column] = pd.Series([value], dtype=object)
    gt, raw, prepared, classes = _prepare(
        predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies
    )
    assert raw.empty
    assert prepared.empty
    assert list(raw.columns) == COLUMNS
    assert calibrate_thresholds(
        gt,
        prepared,
        calibration_split="val",
        classes=classes,
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        confidence_optimization="per_class",
    ) == {"cat": 0.0}


@pytest.mark.parametrize("corners", [(0, 0, 0, 10), (0, 0, 10, 0), (10, 0, 0, 10), (0, 10, 10, 0)])
def test_nonpositive_extent_is_dropped(
    corners: tuple[int, int, int, int], workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame([("valid.jpg", "cat", *corners, 0.8)], columns=COLUMNS)
    _, raw, prepared, _ = _prepare(
        predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies
    )
    assert raw.empty
    assert prepared.empty


@pytest.mark.parametrize("right_corner", ["10", "1_0", "\u0661\u0660"])
@pytest.mark.parametrize("invalid_sibling", [False, True])
def test_valid_numeric_strings_keep_scoring_and_unrelated_validation(
    right_corner: str, invalid_sibling: bool, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame(
        [("valid.jpg", "cat", "0", "0", right_corner, "10", 0.8)],
        columns=COLUMNS,
    )
    if invalid_sibling:
        predictions = pd.concat([predictions, predictions.assign(bbox_x_tl="bad")])
    gt, raw, prepared, classes = _prepare(
        predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies
    )
    assert len(raw) == len(prepared) == 1
    assert calibrate_thresholds(
        gt,
        prepared,
        calibration_split="val",
        classes=classes,
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        confidence_optimization="per_class",
    ) == {"cat": 0.8}
    predictions["confidence"] = float("nan")
    with pytest.raises(ValueError, match="confidence"):
        _prepare(predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies)


def test_geometry_filter_preserves_indices_extras_and_limits_warning_sample() -> None:
    from clearml_yolo.adapters.evaluation.scoring import filter_invalid_prediction_boxes

    predictions = pd.DataFrame(
        [(f"bad-{i}.jpg", "cat", 0, 0, 0, 10, 0.8) for i in range(8)]
        + [("valid.jpg", "cat", 0, 0, 10, 10, 0.8)],
        columns=COLUMNS,
        index=list(range(100, 109)),
    ).assign(extra="retained")
    warnings: list[str] = []
    sink = logger.add(lambda message: warnings.append(str(message)), level="WARNING")
    try:
        filtered = filter_invalid_prediction_boxes(predictions)
        pd.testing.assert_frame_equal(filtered, predictions.iloc[[8]])
        pd.testing.assert_frame_equal(filter_invalid_prediction_boxes(filtered), filtered)
        assert filter_invalid_prediction_boxes(filtered.iloc[:0]).empty
    finally:
        logger.remove(sink)
    assert len(warnings) == 1
    assert "8 of 9" in warnings[0]
    assert "bad-4.jpg" in warnings[0]
    assert "bad-5.jpg" not in warnings[0]


@pytest.mark.parametrize("column", ["bbox_x_br", "image_name", "confidence"])
def test_missing_required_columns_still_fail(
    column: str, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame(
        [("valid.jpg", "cat", 0, 0, 10, 10, 0.8)],
        columns=COLUMNS,
    ).drop(columns=column)
    with pytest.raises(ValueError, match="missing columns"):
        _prepare(predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies)


def test_invalid_ground_truth_still_fails_after_dropping_predictions(
    workflow_dependencies: WorkflowDependencies,
) -> None:
    predictions = pd.DataFrame(
        [("valid.jpg", "cat", 0, 0, 0, 10, 0.8)],
        columns=COLUMNS,
    )
    gt, _, prepared, classes = _prepare(
        predictions, _truth().assign(bbox_x_br=0), EvaluationConfig(), deps=workflow_dependencies
    )
    with pytest.raises(ValueError, match="Ground-truth boxes"):
        calibrate_thresholds(
            gt,
            prepared,
            calibration_split="val",
            classes=classes,
            iou_threshold=0.5,
            matching_strategy="iou_prior",
            confidence_optimization="per_class",
        )


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("confidence", None, "confidence"),
        ("confidence", float("inf"), "confidence"),
        ("confidence", "bad", "confidence"),
        ("confidence", 1.1, "confidence"),
        ("confidence", -0.1, "confidence"),
        ("instance_label", None, "instance_label"),
        ("instance_label", "background", "reserved class"),
    ],
)
def test_dropped_geometry_does_not_hide_unrelated_validation_errors(
    column: str, value: object, message: str, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions = pd.DataFrame(
        [("valid.jpg", "cat", 0, 0, 0, 10, 0.8)],
        columns=COLUMNS,
    )
    predictions[column] = pd.Series([value], dtype=object)
    with pytest.raises(ValueError, match=message):
        _prepare(predictions, _truth(), EvaluationConfig(), deps=workflow_dependencies)
