"""Persisted reports retain producer precision and old payload compatibility."""

import json
from pathlib import Path

import pandas as pd
import pytest
from digital_metrics.scoring import compute_map
from digital_metrics.types import Metrics

from clearml_yolo.adapters.evaluation.scoring import (
    prepare_ground_truth,
    prepare_predictions,
)
from clearml_yolo.application.evaluation import evaluate_split
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.core.evaluation.payload import EvaluationPayload
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)

COLUMNS = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]


@pytest.mark.parametrize("method", ["interp", "continuous"])
@pytest.mark.parametrize("empty_predictions", [False, True])
def test_persisted_report_matches_real_producer_and_roundtrips(
    tmp_path: Path,
    method: str,
    empty_predictions: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    classes = ["кошка", "42"]
    truth = prepare_ground_truth(
        pd.DataFrame(
            [
                ("a", "кошка", 0, 0, 10, 10),
                ("b", "кошка", 0, 0, 10, 10),
                ("empty", None, None, None, None, None),
            ],
            columns=COLUMNS,
        ).assign(split="test"),
        deduplicate=False,
    )
    raw = pd.DataFrame(
        [
            ("a", "кошка", 0, 0, 10, 10, 0.9),
            ("a", "кошка", 0, 0, 10, 10, 0.8),
            ("b", "кошка", 1, 0, 11, 10, 0.1),
            ("empty", "42", 0, 0, 10, 10, 0.7),
        ],
        columns=[*COLUMNS, "confidence"],
    )
    if empty_predictions:
        raw = raw.iloc[:0]
    prepared = prepare_predictions(
        raw,
        preprocess_conf_threshold=0.2,
        preprocess_nms_containment_threshold=0.5,
        preprocess_nms_iou_threshold=None,
    )
    evaluated = evaluate_split(
        truth,
        raw,
        prepared,
        split="test",
        classes=classes,
        thresholds={"кошка": 0.7, "42": 0.7},
        required_classes=classes,
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        ap_method=method,
        skip_cohen_kappa=True,
        output_dir=tmp_path,
        suffix="test",
        deps=workflow_dependencies,
    )
    report = evaluated.evaluation_payload.report
    assert report is not None
    assert evaluated.evaluation_payload.schema_version == report.schema_version == 1
    assert report.classes == classes
    assert report.confusion_matrix == evaluated.confusion_matrix
    assert report.pr_curves == evaluated.pr_curves
    assert report.pr_curves[0].confidence == ([] if empty_predictions else [0.9, 0.8, 0.1])
    authoritative = {name: Metrics() for name in classes}
    compute_map(
        truth.dropna(subset=COLUMNS[2:]),
        raw,
        authoritative,
        ["a", "b", "empty"],
        method=method,
        strategy="iou_prior",
    )
    assert report.average_precisions["кошка"].model_dump() == {
        "ap50": authoritative["кошка"].ap50,
        "ap75": authoritative["кошка"].ap75,
        "ap50_95": authoritative["кошка"].ap50_95,
    }
    assert report.average_precisions["42"].model_dump() == {
        "ap50": None,
        "ap75": None,
        "ap50_95": None,
    }
    if empty_predictions:
        assert report.average_precisions["кошка"].ap50 == 0
    serialized = evaluated.evaluation_payload.model_dump_json()
    assert "NaN" not in serialized
    assert json.loads(serialized)["report"]["average_precisions"]["42"]["ap50"] is None
    assert EvaluationPayload.model_validate_json(serialized) == evaluated.evaluation_payload


def test_legacy_payload_without_report_remains_readable() -> None:
    payload = EvaluationPayload.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "split": "test",
                "image_names": ["empty"],
                "thresholds": {"42": 0.7},
                "ground_truth": [],
                "predictions": [],
                "matches": [],
                "methodology": {"ap_method": "interp"},
            }
        )
    )
    assert payload.report is None
    assert payload.schema_version == 1
    assert payload.methodology == {"ap_method": "interp"}
