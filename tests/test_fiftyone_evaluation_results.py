"""Exact imported matches, persistence, and subset behavior of native results."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

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

    def match(
        gt: int | None, pred: int | None, true: str, predicted: str, status: str
    ) -> dict[str, Any]:
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
    assert results.confusion_matrix(include_missing=True).tolist() == (
        payload.report.confusion_matrix.counts
    )


def test_f1_matches_source_epsilon(native: Any) -> None:
    row = native.DigitalMetricsDetectionResults._class_report(1, 10_000_000, 10_000_000)
    precision = 1 / 10_000_001
    assert row["f1-score"] == pytest.approx(2 * precision * precision / 1e-6)


@pytest.fixture
def dataset(native: Any, payload: EvaluationPayload) -> Iterator[Any]:
    if os.environ.get("CY_TEST_FIFTYONE") != "1":
        pytest.skip("Native database checks require CY_TEST_FIFTYONE=1")
    import fiftyone as fo

    dataset = fo.Dataset(f"cy-native-results-{uuid4().hex}", persistent=True)

    def detections(boxes: Any) -> Any:
        return fo.Detections(
            detections=[
                fo.Detection(
                    label=box.label,
                    bounding_box=[0, 0, 1, 1],
                    confidence=box.confidence,
                    dm_index=box.index,
                )
                for box in boxes
            ]
        )

    try:
        dataset.add_sample(
            fo.Sample(
                filepath="/tmp/native-result-image.png",
                image_name="image.png",
                split="test",
                gt=detections(payload.ground_truth),
                pred=detections([box for box in payload.predictions if box.status != "filtered"]),
            ),
            dynamic=True,
        )
        yield dataset
    finally:
        dataset.delete()


def test_native_api_persistence_subset_alignment_and_lifecycle(
    native: Any,
    payload: EvaluationPayload,
    dataset: Any,
) -> None:
    import fiftyone as fo

    results = native.publish_evaluation(
        dataset,
        dataset.view(),
        payload,
        "native_eval",
        "gt",
        "pred",
        run_key="run",
    )
    assert dataset.list_evaluations() == ["native_eval"]
    assert dataset.get_evaluation_info("native_eval").config.cy_run_key == "run"
    assert dataset.get_evaluation_info("native_eval").config.thresholds == payload.thresholds
    sample = dataset.first()
    assert sample.gt.detections[0]["native_eval_id"] == sample.pred.detections[0].id
    assert sample.pred.detections[0]["native_eval_id"] == sample.gt.detections[0].id
    assert sample.gt.detections[1]["native_eval"] == "fn"
    assert len(sample.pred.detections) == 4
    assert (sample.native_eval_tp, sample.native_eval_fp, sample.native_eval_fn) == (1, 3, 2)
    loaded = dataset.load_evaluation_results("native_eval", cache=False)
    assert isinstance(loaded, native.DigitalMetricsDetectionResults)
    assert loaded.source_payload == payload
    script = """
import json
import sys
import fiftyone as fo
dataset = fo.load_dataset(sys.argv[1])
results = dataset.load_evaluation_results('native_eval', cache=False)
info = dataset.get_evaluation_info('native_eval')
print(json.dumps({'class': results.cls, 'method': info.config.method,
                  'run_key': info.config.cy_run_key, 'counts': results.tp_fp_fn(),
                  'report': results.report_payload.model_dump(mode='json'),
                  'ap': results.mAP()}))
"""
    process = subprocess.run(  # noqa: S603 - fixed test program, UUID-owned dataset
        [sys.executable, "-c", script, dataset.name],
        check=True,
        capture_output=True,
        text=True,
    )
    fresh = json.loads(process.stdout.strip().splitlines()[-1])
    assert fresh["class"].endswith(".DigitalMetricsDetectionResults")
    assert fresh["method"] == "digital_metrics"
    assert fresh["run_key"] == "run"
    assert fresh["counts"] == [1, 3, 2]
    assert fresh["ap"] == pytest.approx(0.25)
    assert fresh["report"] == (payload.report.model_dump(mode="json") if payload.report else None)
    assert len(dataset.load_evaluation_view("native_eval")) == 1
    patches = dataset.to_evaluation_patches("native_eval")
    assert len(patches) > 0
    assert set(patches.values("type")) <= {"tp", "fp", "fn"}

    originals = {
        name: getattr(results, name).copy()
        for name in (
            "ytrue",
            "ypred",
            "ious",
            "confs",
            "ytrue_ids",
            "ypred_ids",
        )
    }
    subset = dataset.filter_labels("gt", fo.ViewField("dm_index") == 2).filter_labels(
        "pred",
        fo.ViewField("dm_index") == 1,
    )
    with results.use_subset(subset):
        assert bool(results.is_subset)
        assert all(len(getattr(results, name)) == 2 for name in originals)
        assert results.tp_fp_fn() == (0, 1, 1)
        assert results.mAP() is None
        with pytest.raises(ValueError, match="unavailable"):
            results.plot_pr_curves()
        assert results.label_ids("matrix", x="dog", y="background") == (
            [],
            [sample.pred.detections[1].id],
        )
    assert not results.is_subset
    for name, original in originals.items():
        assert getattr(results, name).tolist() == original.tolist()
    with results.use_subset(dataset.view()):
        assert not results.is_subset
        assert results.mAP() == pytest.approx(0.25)
    dataset.rename_evaluation("native_eval", "renamed")
    assert dataset.list_evaluations() == ["renamed"]
    assert dataset.load_evaluation_results("renamed", cache=False).tp_fp_fn() == (1, 3, 2)
    dataset.delete_evaluation("renamed")
    assert dataset.list_evaluations() == []
    assert "renamed_tp" not in dataset.get_field_schema()


def test_ap_scope_accounts_for_unmatched_images_and_removed_labels(
    native: Any,
    payload: EvaluationPayload,
    dataset: Any,
) -> None:
    import fiftyone as fo

    payload.image_names.append("empty.png")
    dataset.add_sample(
        fo.Sample(
            filepath="/tmp/native-empty.png",
            image_name="empty.png",
            split="test",
            gt=fo.Detections(),
            pred=fo.Detections(),
        )
    )
    results = native.publish_evaluation(
        dataset,
        dataset.view(),
        payload,
        "native_eval",
        "gt",
        "pred",
        run_key="run",
    )
    with results.use_subset(dataset.match(fo.ViewField("image_name") == "image.png")):
        assert bool(results.is_subset)
        assert results.mAP() is None
        assert len(results.ytrue) == 5
    with results.use_subset(dataset.filter_labels("gt", fo.ViewField("dm_index") != 1)):
        assert bool(results.is_subset)
        assert results.mAP() is None
        assert len(results.ytrue) == 5


def test_empty_native_evaluation_subset_report_and_restoration(
    native: Any,
    payload: EvaluationPayload,
    dataset: Any,
) -> None:
    import fiftyone as fo

    payload.ground_truth = []
    payload.predictions = []
    payload.matches = []
    assert payload.report is not None
    payload.report.confusion_matrix.counts = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    payload.report.pr_curves = []
    for ap in payload.report.average_precisions.values():
        ap.ap50 = ap.ap75 = ap.ap50_95 = None
    sample = dataset.first()
    sample.gt = fo.Detections()
    sample.pred = fo.Detections()
    sample.save()
    results = native.publish_evaluation(
        dataset,
        dataset.view(),
        payload,
        "native_eval",
        "gt",
        "pred",
        run_key="run",
    )
    results = dataset.load_evaluation_results("native_eval", cache=False)
    fields = ("ytrue", "ypred", "ious", "confs", "weights", "ytrue_ids", "ypred_ids")
    originals = {name: getattr(results, name) for name in fields}
    original_samples = results.samples
    with results.use_subset(dataset.view()):
        assert results.has_subset
        assert not results.is_subset
        assert all(
            getattr(results, name) is None or len(getattr(results, name)) == 0 for name in fields
        )
        assert results.tp_fp_fn() == (0, 0, 0)
        assert results.report()["cat"]["support"] == 0
        assert results.metrics()["precision"] == 0
        assert results.confusion_matrix(include_missing=True).tolist() == [[0] * 3] * 3
        assert results.mAP() is None
        assert len(results.plot_pr_curves().data) == 0
        assert results.label_ids("matrix", x="cat", y="cat") == ([], [])
    assert not results.has_subset
    assert results.samples is original_samples
    assert all(getattr(results, name) is value for name, value in originals.items())
    with results.use_subset({"type": "field", "field": "split", "value": "absent"}):
        assert bool(results.is_subset)
        assert results.tp_fp_fn() == (0, 0, 0)
        assert results.mAP() is None
        with pytest.raises(ValueError, match="unavailable"):
            results.plot_pr_curves()
    assert all(getattr(results, name) is value for name, value in originals.items())
