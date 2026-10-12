"""Export numerical matching and genuine COCO quality are separate acceptance gates."""

from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from clearml_yolo.adapters.export.quality import evaluate_detections
from clearml_yolo.core.datasets import Box, ImageRecord
from clearml_yolo.core.export_quality import QualityMetrics, match_detections, quality_gate


def _array(rows: list[list[float]]) -> NDArray[np.float32]:
    return np.asarray(rows, dtype=np.float32).reshape(-1, 6)


def _image(name: str, boxes: list[Box]) -> ImageRecord:
    return ImageRecord(name=name, path=Path(name), width=128, height=128, split="val", boxes=boxes)


def _box(label: str = "square", offset: float = 0) -> Box:
    return Box(label=label, x1=10 + offset, y1=10, x2=20 + offset, y2=20)


def _metrics(value: float) -> QualityMetrics:
    return QualityMetrics(mAP=value, map50=value, recall=value, per_class_recall={"square": value})


def test_detection_matching_ignores_permutation_and_tracks_numerical_error() -> None:
    native = _array([[0, 0, 10, 10, 0.9, 0], [20, 20, 30, 30, 0.8, 1]])
    exported = native[::-1].copy()
    exported[1, 0] += 0.001
    exported[1, 4] -= 0.002
    agreement = match_detections(native, exported)
    assert agreement.matched == 2
    assert agreement.unmatched_reference == 0
    assert agreement.unmatched_exported == 0
    assert agreement.max_box_error == pytest.approx(0.001)
    assert agreement.max_score_error == pytest.approx(0.002, abs=1e-6)


def test_matching_is_class_aware_and_one_to_one() -> None:
    native = _array([[0, 0, 10, 10, 0.9, 0], [0, 0, 10, 10, 0.8, 0]])
    exported = _array([[0, 0, 10, 10, 0.9, 0], [0, 0, 10, 10, 0.8, 1]])
    agreement = match_detections(native, exported)
    assert agreement.matched == 1
    assert agreement.unmatched_reference == 1
    assert agreement.unmatched_exported == 1


def test_matching_maximizes_valid_cardinality_before_iou() -> None:
    native = _array([[0, 0, 10, 10, 0.9, 0], [3, 0, 13, 10, 0.8, 0]])
    exported = _array([[0, 0, 10, 10, 0.9, 0], [-3, 0, 7, 10, 0.8, 0]])
    assert match_detections(native, exported, min_iou=0.5).matched == 2


def test_empty_and_unmatched_numerical_results_have_no_fabricated_error() -> None:
    agreement = match_detections(_array([]), _array([[0, 0, 10, 10, 0.9, 0]]))
    assert agreement.matched == 0
    assert agreement.unmatched_exported == 1
    assert agreement.max_box_error is None
    assert agreement.max_score_error is None


@pytest.mark.parametrize(
    "rows",
    [
        [[0, 0, 10, 10, float("nan"), 0]],
        [[0, 0, 10, 10, 0.9, 0.5]],
        [[0, 0, 10, 10, 0.9, -1]],
        [[10, 0, 0, 10, 0.9, 0]],
        [[0, 0, 10, 10, 1.1, 0]],
    ],
)
def test_matching_rejects_invalid_detection_rows(rows: list[list[float]]) -> None:
    with pytest.raises(ValueError, match="Detection"):
        match_detections(_array(rows), _array([]))


def test_matching_rejects_invalid_shape_and_threshold() -> None:
    with pytest.raises(ValueError, match="Nx6"):
        match_detections(np.zeros((2, 5), dtype=np.float32), _array([]))
    with pytest.raises(ValueError, match="min_iou"):
        match_detections(_array([]), _array([]), min_iou=float("nan"))


def test_quality_gate_requires_positive_grounded_reference() -> None:
    assert not quality_gate(_metrics(0), _metrics(0), precision="fp32", reference_detection_count=1)
    assert not quality_gate(
        _metrics(0.5), _metrics(0.5), precision="fp32", reference_detection_count=0
    )
    assert quality_gate(
        _metrics(0.5), _metrics(0.499), precision="fp32", reference_detection_count=1
    )
    assert not quality_gate(
        _metrics(0.5), _metrics(0.498), precision="fp32", reference_detection_count=1
    )
    assert quality_gate(
        _metrics(0.5), _metrics(0.495), precision="fp16", reference_detection_count=1
    )
    assert not quality_gate(
        _metrics(0.5), _metrics(0.494), precision="fp16", reference_detection_count=1
    )


def test_quality_gate_rejects_nonfinite_metrics_even_when_validation_was_bypassed() -> None:
    invalid = _metrics(0.5).model_copy(update={"mAP": float("nan")})
    assert not quality_gate(invalid, _metrics(0.5), precision="fp32", reference_detection_count=1)


def test_identical_wrong_boxes_agree_numerically_but_fail_quality_gate() -> None:
    images = [_image("positive.png", [_box()]), _image("negative.png", [])]
    detections = {"positive.png": _array([[50, 50, 60, 60, 0.9, 0]]), "negative.png": _array([])}
    assert match_detections(detections["positive.png"], detections["positive.png"]).matched == 1
    quality = evaluate_detections(images, ["square"], detections)
    assert quality.mAP == 0
    assert not quality_gate(quality, quality, precision="fp32", reference_detection_count=1)


def test_perfect_coco_detection_retains_empty_images_and_class_recall() -> None:
    images = [_image("positive.png", [_box(), _box("circle", 30)]), _image("negative.png", [])]
    detections = {
        "positive.png": _array([[10, 10, 20, 20, 0.9, 0], [40, 10, 50, 20, 0.8, 1]]),
        "negative.png": _array([]),
    }
    quality = evaluate_detections(images, ["square", "circle"], detections)
    assert quality.mAP == pytest.approx(1)
    assert quality.map50 == pytest.approx(1)
    assert quality.recall == pytest.approx(1)
    assert quality.per_class_recall == {"square": 1, "circle": 1}
    detections["negative.png"] = _array([[10, 10, 20, 20, 0.99, 0]])
    assert evaluate_detections(images, ["square", "circle"], detections).mAP < quality.mAP


def test_coco_fixed_max_detections_100_applies_to_crowded_images() -> None:
    boxes = [
        Box(
            label="square",
            x1=(i % 10) * 10,
            y1=(i // 10) * 10,
            x2=(i % 10) * 10 + 5,
            y2=(i // 10) * 10 + 5,
        )
        for i in range(101)
    ]
    image = _image("crowded.png", boxes)
    detections = {
        "crowded.png": _array([[box.x1, box.y1, box.x2, box.y2, 0.9, 0] for box in boxes])
    }
    quality = evaluate_detections([image], ["square"], detections)
    assert quality.recall == pytest.approx(100 / 101)
    assert quality.per_class_recall["square"] == pytest.approx(100 / 101)


@pytest.mark.parametrize("keys", [[], ["positive.png", "unexpected.png"]])
def test_coco_population_must_match_exact_image_paths(keys: list[str]) -> None:
    images = [_image("positive.png", [_box()])]
    with pytest.raises(ValueError, match="population"):
        evaluate_detections(images, ["square"], {key: _array([]) for key in keys})


def test_coco_rejects_unknown_ground_truth_and_prediction_classes() -> None:
    with pytest.raises(ValueError, match="ground-truth class"):
        evaluate_detections(
            [_image("positive.png", [_box("unknown")])], ["square"], {"positive.png": _array([])}
        )
    with pytest.raises(ValueError, match="prediction class"):
        evaluate_detections(
            [_image("positive.png", [_box()])],
            ["square"],
            {"positive.png": _array([[10, 10, 20, 20, 0.9, 1]])},
        )


def test_empty_predictions_and_empty_truth_return_zero_metrics() -> None:
    metrics = evaluate_detections([_image("empty.png", [])], ["square"], {"empty.png": _array([])})
    assert metrics == _metrics(0)


def test_empty_population_cannot_establish_quality() -> None:
    metrics = evaluate_detections([], ["square"], {})
    assert metrics == _metrics(0)
    assert not quality_gate(metrics, metrics, precision="fp32", reference_detection_count=0)


def test_duplicate_boxes_match_scores_under_permutation() -> None:
    native = _array([[0, 0, 10, 10, 0.9, 0], [0, 0, 10, 10, 0.8, 0]])
    agreement = match_detections(native, native[::-1])
    assert agreement.matched == 2
    assert agreement.max_score_error == 0


def test_all_zero_export_quality_cannot_pass_a_weak_positive_baseline() -> None:
    assert not quality_gate(
        _metrics(0.0001), _metrics(0), precision="fp32", reference_detection_count=1
    )


def test_evaluator_identity_binds_real_module_version_and_source_hash() -> None:
    from clearml_yolo.adapters.export.quality import evaluator_identity

    identity = evaluator_identity()
    assert identity["module"] == "pycocotools.cocoeval"
    assert identity["class"] == "COCOeval"
    assert identity["package_version"]
    assert len(identity["source_sha256"]) == 64


def test_evaluator_alias_contamination_fails_before_quality_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    from types import ModuleType

    from clearml_yolo.adapters.export.quality import evaluator_identity

    replacement = ModuleType("pycocotools.cocoeval")
    replacement_type = type(
        "COCOeval",
        (),
        {"__module__": "faster_coco_eval.core.faster_eval_api"},
    )
    replacement.COCOeval = replacement_type  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pycocotools.cocoeval", replacement)
    with pytest.raises(ValueError, match="actual pycocotools"):
        evaluator_identity()
    with pytest.raises(ValueError, match="actual pycocotools"):
        evaluate_detections(
            [_image("positive.png", [_box()])], ["square"], {"positive.png": _array([])}
        )
