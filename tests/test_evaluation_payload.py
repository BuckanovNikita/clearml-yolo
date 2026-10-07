"""Neutral evaluation payloads preserve exact fixed-threshold evidence."""

from pathlib import Path

import pandas as pd
import pytest
from digital_metrics.matching import match_boxes
from digital_metrics.scoring import slice_by_conf

from clearml_yolo.comparison.evaluation_payload import (
    EvaluationBox,
    EvaluationMatch,
    EvaluationPayload,
)
from clearml_yolo.comparison.scoring import build_evaluation_payload
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.metrics import EvaluationConfig, compute_metrics

GT_COLUMNS = [
    "image_name",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
]
PRED_COLUMNS = [*GT_COLUMNS, "confidence"]


def test_payload_json_round_trip_preserves_schema_and_methodology() -> None:
    payload = EvaluationPayload(
        split="test",
        image_names=["0007.jpg"],
        thresholds={"7": 0.5},
        ground_truth=[
            EvaluationBox(
                index=11,
                image_name="0007.jpg",
                label="7",
                box=(1.0, 2.0, 9.0, 10.0),
                status="TP",
            )
        ],
        predictions=[
            EvaluationBox(
                index=21,
                image_name="0007.jpg",
                label="7",
                box=(1.0, 2.0, 9.0, 10.0),
                confidence=0.9,
                status="TP",
            )
        ],
        matches=[
            EvaluationMatch(
                gt_index=11,
                pred_index=21,
                gt_label="7",
                pred_label="7",
                confidence=0.9,
                iou=1.0,
                status="TP",
            )
        ],
        methodology={"iou_threshold": 0.5, "matching_strategy": "iou_prior"},
    )

    restored = EvaluationPayload.model_validate_json(payload.model_dump_json())

    assert restored == payload
    assert restored.schema_version == 1
    assert restored.ground_truth[0].confidence is None


def test_payload_uses_sliced_matches_and_preserves_backgrounds_and_filtered_boxes() -> None:
    ground_truth = pd.DataFrame(
        [
            ("tp.jpg", 7, 0.0, 0.0, 10.0, 10.0),
            ("wrong.jpg", 7, 0.0, 0.0, 10.0, 10.0),
            ("miss.jpg", 7, 0.0, 0.0, 10.0, 10.0),
            ("filtered.jpg", 7, 0.0, 0.0, 10.0, 10.0),
            ("background.jpg", None, None, None, None, None),
        ],
        columns=GT_COLUMNS,
        index=[100, 101, 102, 103, 104],
    )
    ground_truth["instance_label"] = pd.Series(
        [7, 7, 7, 7, None], index=ground_truth.index, dtype=object
    )
    predictions = pd.DataFrame(
        [
            ("tp.jpg", 7, 0.0, 0.0, 10.0, 10.0, 0.9),
            ("wrong.jpg", 8, 0.0, 0.0, 10.0, 10.0, 0.8),
            ("background.jpg", 8, 20.0, 20.0, 30.0, 30.0, 0.7),
            ("filtered.jpg", 7, 0.0, 0.0, 10.0, 10.0, 0.4),
            ("other.jpg", 7, 0.0, 0.0, 10.0, 10.0, 0.95),
        ],
        columns=PRED_COLUMNS,
        index=[200, 201, 202, 203, 204],
    )
    image_names = ["tp.jpg", "wrong.jpg", "miss.jpg", "filtered.jpg", "background.jpg"]
    matches = match_boxes(
        ground_truth,
        predictions,
        0.5,
        strategy="iou_prior",
        split_image_names=image_names,
    )
    sliced = slice_by_conf(matches, ["7", "8"], {"7": 0.5, "8": 0.5})

    payload = build_evaluation_payload(
        ground_truth,
        predictions,
        split="test",
        image_names=image_names,
        thresholds={"7": 0.5, "8": 0.5},
        sliced=sliced,
        methodology={"iou_threshold": 0.5},
    )

    assert payload.image_names == image_names
    assert [(box.index, box.label, box.status) for box in payload.ground_truth] == [
        (100, "7", "TP"),
        (101, "7", "FN"),
        (102, "7", "FN"),
        (103, "7", "FN"),
    ]
    assert [(box.index, box.label, box.status) for box in payload.predictions] == [
        (200, "7", "TP"),
        (201, "8", "FP"),
        (202, "8", "FP"),
        (203, "7", "filtered"),
    ]
    assert all(box.image_name != "other.jpg" for box in payload.predictions)

    by_indices = {(match.gt_index, match.pred_index): match for match in payload.matches}
    assert by_indices[(100, 200)].status == "TP"
    assert by_indices[(100, 200)].iou == pytest.approx(1.0)
    assert by_indices[(101, 201)].status == "FP"
    assert by_indices[(101, 201)].gt_label == "7"
    assert by_indices[(101, 201)].pred_label == "8"
    assert by_indices[(101, 201)].iou == pytest.approx(1.0)
    assert by_indices[(101, None)].status == "FN"
    assert by_indices[(None, 202)].status == "FP"
    assert by_indices[(None, 202)].gt_label == "background"
    assert by_indices[(None, 202)].iou is None
    assert by_indices[(103, None)].status == "FN"
    assert all(match.pred_index != 203 for match in payload.matches)


def test_metrics_retains_local_payload_and_publishes_readable_workbook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ground_truth = pd.DataFrame(
        [
            ("val.jpg", "/images/val.jpg", "cat", 0, 0, 10, 10, "val"),
            ("test.jpg", "/images/test.jpg", "cat", 0, 0, 10, 10, "test"),
            ("background.jpg", "/images/background.jpg", None, None, None, None, None, "test"),
        ],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    predictions = pd.DataFrame(
        [
            ("val.jpg", "cat", 0, 0, 10, 10, 0.8),
            ("test.jpg", "cat", 0, 0, 10, 10, 0.9),
            ("background.jpg", "cat", 20, 20, 30, 30, 0.2),
        ],
        columns=PRED_COLUMNS,
    )
    ground_truth_path = tmp_path / "ground_truth.csv"
    predictions_path = tmp_path / "predictions.csv"
    ground_truth.to_csv(ground_truth_path, index=False)
    predictions.to_csv(predictions_path, index=False)
    from test_metrics import _metric_owner

    with _metric_owner(monkeypatch) as task:
        result = compute_metrics(
            predictions_path,
            ground_truth_path,
            tmp_path / "metrics",
            clearml=object(),  # type: ignore[arg-type]
            evaluation=EvaluationConfig(iou_threshold=0.5),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="test model",
        )

    uploaded = {item["name"]: item["artifact_object"] for item in task.uploads}
    payload_path = result.evaluations["test"]
    payload = EvaluationPayload.model_validate_json(payload_path.read_text(encoding="utf-8"))
    assert payload_path == tmp_path / "metrics" / "evaluation_test.json"
    assert payload.image_names == ["test.jpg", "background.jpg"]
    assert payload.methodology == EvaluationConfig(iou_threshold=0.5).model_dump(mode="json")
    assert [(box.index, box.status) for box in payload.predictions] == [
        (1, "TP"),
        (2, "filtered"),
    ]
    assert "predicts_csv" in uploaded
    workbook = uploaded["metrics_dashboard_full_test"]
    assert workbook.suffix == ".xlsx"
    assert payload_path not in uploaded.values()
