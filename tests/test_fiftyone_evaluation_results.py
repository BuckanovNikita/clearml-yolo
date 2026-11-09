"""Exact imported matches of native results; database persistence and subsets live in
tests/integration/fiftyone/test_fiftyone_native_evaluations.py."""

from typing import Any

import pytest

from clearml_yolo.core.evaluation.payload import EvaluationPayload


@pytest.fixture
def native(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("FIFTYONE_DISABLE_SERVICES", "1")
    from clearml_yolo.adapters.fiftyone import evaluation as fiftyone_evaluation

    return fiftyone_evaluation


@pytest.fixture
def payload() -> EvaluationPayload:
    def box(index: int, label: str, status: str) -> dict[str, Any]:
        return {
            "index": index,
            "image_name": "image.png",
            "label": label,
            "box": [0, 0, 1, 1],
            "status": status,
        }

    def match(gt: int | None, pred: int | None, true: str, predicted: str, status: str) -> dict[str, Any]:
        return {
            "gt_index": gt,
            "pred_index": pred,
            "gt_label": true,
            "pred_label": predicted,
            "confidence": 0.8,
            "iou": 0.7 if gt is not None and pred is not None else None,
            "status": status,
        }

    return EvaluationPayload.model_validate(
        {
            "split": "test",
            "image_names": ["image.png"],
            "thresholds": {"cat": 0.5, "dog": 0.5},
            "ground_truth": [box(0, "cat", "TP"), box(1, "cat", "FN"), box(2, "dog", "FN")],
            "predictions": [
                box(0, "cat", "TP"),
                box(1, "dog", "FP"),
                box(2, "dog", "FP"),
                box(3, "cat", "FP"),
                box(4, "dog", "filtered"),
            ],
            "matches": [
                match(0, 0, "cat", "cat", "TP"),
                match(1, 3, "cat", "cat", "FP"),
                match(0, 1, "cat", "dog", "FP"),
                match(1, 2, "cat", "dog", "FP"),
                match(1, None, "cat", "background", "FN"),
                match(2, None, "dog", "background", "FN"),
            ],
            "report": {
                "classes": ["cat", "dog"],
                "confusion_matrix": {
                    "labels": ["cat", "dog", "background"],
                    "counts": [[2, 0, 0], [0, 0, 1], [0, 2, 0]],
                },
                "pr_curves": [
                    {
                        "class_name": "cat",
                        "recall": [0.5, 1.0],
                        "precision": [1.0, 0.5],
                        "confidence": [0.9, 0.7],
                        "tp": [1, 2],
                        "fp": [0, 2],
                        "gt_count": 2,
                        "ap50": 0.7,
                        "integration_method": "interp",
                    }
                ],
                "average_precisions": {
                    "cat": {"ap50": 0.7, "ap75": 0.5, "ap50_95": 0.4},
                    "dog": {"ap50": 0.2, "ap75": 0.1, "ap50_95": 0.1},
                },
            },
        }
    )


def _results(native: Any, payload: EvaluationPayload) -> Any:
    gt_ids = {box.index: f"gt{box.index}" for box in payload.ground_truth}
    pred_ids = {box.index: f"pred{box.index}" for box in payload.predictions}
    config = native.DigitalMetricsEvaluationConfig("pred", "gt", cy_run_key="run")
    return native.DigitalMetricsDetectionResults(
        None,
        config,
        "eval",
        native.canonical_matches(payload, gt_ids, pred_ids),
        source_payload=payload.model_dump(mode="json"),
        ground_truth_ids={str(k): v for k, v in gt_ids.items()},
        prediction_ids={str(k): v for k, v in pred_ids.items()},
    )


def test_canonical_tuples_claim_tp_then_first_fp_and_keep_source(
    native: Any,
    payload: EvaluationPayload,
) -> None:
    results = _results(native, payload)
    assert list(zip(results.ytrue, results.ypred, strict=True)) == [
        ("cat", "cat"),
        ("cat", "cat"),
        ("background", "dog"),
        ("background", "dog"),
        ("dog", "background"),
    ]
    assert results.source_payload == payload
    assert results.tp_fp_fn() == (1, 3, 2)
    assert results.report()["cat"]["precision"] == pytest.approx(0.5)
    assert results.report()["cat"]["recall"] == pytest.approx(0.5)
    assert results.metrics()["precision"] == pytest.approx(0.25)
    assert results.confusion_matrix(include_missing=True).tolist() == (
        payload.report.confusion_matrix.counts if payload.report else None
    )
    assert results.label_ids("matrix", x="dog", y="background") == ([], ["pred1", "pred2"])


def test_serialization_retains_report_ids_and_ap(native: Any, payload: EvaluationPayload) -> None:
    results = _results(native, payload)
    loaded = native.DigitalMetricsDetectionResults.from_dict(
        results.serialize(),
        None,
        results.config,
        "eval",
    )
    assert loaded.config.method == "digital_metrics"
    assert loaded.source_payload == payload
    assert loaded.tp_fp_fn() == (1, 3, 2)
    assert loaded.mAP() == pytest.approx(0.25)
    assert loaded.label_ids("field", status="FN") == (["gt1", "gt2"], [])
    figure = loaded.plot_pr_curves()
    assert list(figure.data[0].x) == [0.5, 1.0]
    assert list(figure.data[0].y) == [1.0, 0.5]
    assert not hasattr(loaded, "mAR")


def test_old_payload_has_no_invented_ap(native: Any, payload: EvaluationPayload) -> None:
    payload.report = None
    results = _results(native, payload)
    assert results.mAP() is None
    with pytest.raises(ValueError, match="unavailable"):
        results.plot_pr_curves()


def test_report_confusion_disagreement_rejected(native: Any, payload: EvaluationPayload) -> None:
    assert payload.report is not None
    payload.report.confusion_matrix.counts[0][0] += 1
    with pytest.raises(ValueError, match="confusion matrix"):
        _results(native, payload)


def test_wrong_class_pair_claims_gt_and_retains_source_fn(
    native: Any,
    payload: EvaluationPayload,
) -> None:
    payload.matches = [match for match in payload.matches if match.pred_index != 3]
    payload.predictions = [box for box in payload.predictions if box.index != 3]
    assert payload.report is not None
    payload.report.confusion_matrix.counts = [[1, 1, 0], [0, 0, 1], [0, 1, 0]]
    results = _results(native, payload)
    assert results.label_ids("matrix", x="dog", y="cat") == (["gt1"], ["pred2"])
    assert results.label_ids("matrix", x="dog", y="background") == ([], ["pred1"])
    assert results.tp_fp_fn() == (1, 2, 2)
    assert results.report()["cat"]["recall"] == pytest.approx(0.5)
    assert results.confusion_matrix(include_missing=True).tolist() == (payload.report.confusion_matrix.counts)


def test_f1_matches_source_epsilon(native: Any) -> None:
    row = native.DigitalMetricsDetectionResults._class_report(1, 10_000_000, 10_000_000)
    precision = 1 / 10_000_001
    assert row["f1-score"] == pytest.approx(2 * precision * precision / 1e-6)
