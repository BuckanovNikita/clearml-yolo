"""Export numerical matching and genuine COCO quality are separate acceptance gates."""

import re
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pytest
from numpy.typing import NDArray

from clearml_yolo.adapters.export.quality import evaluate_detections
from clearml_yolo.core.datasets import Box, ImageRecord
from clearml_yolo.core.export_quality import (
    QualityMetrics,
    match_detections,
    quality_gate,
    validate_detections,
)


def _array(rows: list[list[float]]) -> NDArray[np.float32]:
    return np.asarray(rows, dtype=np.float32).reshape(-1, 6)


def _rows(values: list[list[float]]) -> NDArray[np.float64]:
    return np.asarray(values, dtype=np.float64).reshape(-1, 6)


def _image(name: str, boxes: list[Box]) -> ImageRecord:
    return ImageRecord(name=name, path=Path(name), width=128, height=128, split="val", boxes=boxes)


def _box(label: str = "square", offset: float = 0) -> Box:
    return Box(label=label, x1=10 + offset, y1=10, x2=20 + offset, y2=20)


def _metrics(value: float = 0.5) -> QualityMetrics:
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


@pytest.mark.parametrize(
    "scores",
    [
        (0.9, 0.8, 0.9, 0.8),
        (8.916139000238107e-8, 5.5140087729750384e-8, 6.682907458007322e-6, 3.0820231403132725e-7),
    ],
)
def test_matching_is_class_aware_and_one_to_one(scores: tuple[float, float, float, float]) -> None:
    native = _rows([[0, 0, 10, 10, score, 0] for score in scores[:2]])
    exported = _rows([[0, 0, 10, 10, scores[2], 0], [0, 0, 10, 10, scores[3], 2]])
    agreement = match_detections(native, exported)
    assert agreement.matched == 1
    assert agreement.unmatched_reference == 1
    assert agreement.unmatched_exported == 1
    assert agreement.max_score_error == min(abs(score - scores[2]) for score in scores[:2])


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


@pytest.mark.parametrize("images", [[], [_image("empty.png", [])]])
def test_empty_predictions_and_empty_truth_return_zero_metrics(images: list[ImageRecord]) -> None:
    metrics = evaluate_detections(images, ["square"], {image.name: _array([]) for image in images})
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


@pytest.mark.parametrize(
    ("values", "diagnostic"),
    [
        (np.zeros(6), "Detections must have shape Nx6"),
        (np.zeros((1, 5)), "Detections must have shape Nx6"),
        (
            np.array([[0, 0, 4, 2, 1, 0]], dtype=str),
            "Detection rows must contain real numeric values",
        ),
        (np.ones((1, 6), dtype=np.complex128), "Detection rows must contain real numeric values"),
        (np.ones((1, 6), dtype=np.bool_), "Detection rows must contain real numeric values"),
        (_rows([[0, 0, 4, 2, np.inf, 0]]), "Detection rows must contain finite values"),
        (_rows([[0, 0, 4, 2, np.nan, 0]]), "Detection rows must contain finite values"),
        (_rows([[0, 0, 0, 2, 0.5, 0]]), "Detection box width and height must be positive"),
        (_rows([[0, 0, 4, 0, 0.5, 0]]), "Detection box width and height must be positive"),
        (_rows([[4, 0, 0, 2, 0.5, 0]]), "Detection box width and height must be positive"),
        (_rows([[0, 0, 4, 2, -0.1, 0]]), "Detection confidence must be between zero and one"),
        (_rows([[0, 0, 4, 2, 1.1, 0]]), "Detection confidence must be between zero and one"),
        (
            _rows([[0, 0, 4, 2, 0.5, -1]]),
            "Detection labels must be zero-based nonnegative integers",
        ),
        (
            _rows([[0, 0, 4, 2, 0.5, 0.5]]),
            "Detection labels must be zero-based nonnegative integers",
        ),
    ],
)
@pytest.mark.parametrize("side", ["native", "exported"])
def test_detection_validation_reports_the_invalid_boundary(
    values: NDArray[Any], diagnostic: str, side: str
) -> None:
    native, exported = (values, _rows([])) if side == "native" else (_rows([]), values)
    with pytest.raises(ValueError, match=f"^{re.escape(diagnostic)}$"):
        match_detections(native, exported)


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_detection_validation_retains_confidence_endpoints_and_normalizes_dtype(
    confidence: float,
) -> None:
    original = np.asarray([[1, 2, 5, 4, confidence, 0]], dtype=np.float32)
    validated = validate_detections(original)
    assert validated.dtype == np.float64
    np.testing.assert_array_equal(validated, original)


@pytest.mark.parametrize("min_iou", [-1.0, 0.0, 1.01, 2.0, np.nan, np.inf, -np.inf])
def test_match_threshold_rejects_values_outside_open_closed_unit_interval(min_iou: float) -> None:
    message = "min_iou must be finite and between zero (exclusive) and one"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        match_detections(_rows([]), _rows([]), min_iou=min_iou)


@pytest.mark.parametrize(("native_count", "served_count"), [(0, 0), (0, 1), (1, 0)])
def test_empty_sides_retain_counts_without_numerical_error(
    native_count: int, served_count: int
) -> None:
    box = [0.0, 0.0, 1e200, 1e200, 0.5, 0.0]
    with np.errstate(over="raise", invalid="raise"):
        result = match_detections(_rows([box] * native_count), _rows([box] * served_count))
    assert result.model_dump() == {
        "matched": 0,
        "unmatched_reference": native_count,
        "unmatched_exported": served_count,
        "max_box_error": None,
        "max_score_error": None,
    }


@pytest.mark.parametrize(
    ("box", "min_iou", "matched"),
    [
        ([0, 0, 4, 2, 0.5, 0], 1.0, 1),
        ([2, 0, 6, 2, 0.5, 0], 1 / 3, 1),
        ([2, 0, 6, 2, 0.5, 0], np.nextafter(1 / 3, 1.0), 0),
        ([5, 0, 9, 2, 0.5, 0], 0.1, 0),
    ],
)
def test_nonsquare_boxes_match_at_the_geometric_iou_boundary(
    box: list[float], min_iou: float, matched: int
) -> None:
    result = match_detections(_rows([[0, 0, 4, 2, 0.5, 0]]), _rows([box]), min_iou=min_iou)
    assert result.matched == matched
    assert result.unmatched_reference == result.unmatched_exported == 1 - matched


def test_matching_prefers_closer_geometry_among_valid_candidates() -> None:
    native = _rows([[0, 0, 10, 2, 0.9, 0]])
    served = _rows([[1, 0, 11, 2, 0.1, 0], [0.5, 0, 10.5, 2, 0.89, 0]])
    result = match_detections(native, served, min_iou=0.5)
    assert result.matched == 1
    assert result.unmatched_exported == 1
    assert result.max_box_error == 0.5
    assert result.max_score_error == pytest.approx(0.01)


@pytest.mark.parametrize(("offset", "min_iou"), [(3.0, 0.5), (9.0, 0.05), (10 - 1e-9, 1e-12)])
def test_match_cardinality_precedes_geometry_and_score_for_small_overlaps(
    offset: float, min_iou: float
) -> None:
    native = _rows([[0, 0, 10, 2, 0, 0], [offset, 0, 10 + offset, 2, 1, 0]])
    served = _rows([[0, 0, 10, 2, 0, 0], [-offset, 0, 10 - offset, 2, 1, 0]])
    result = match_detections(native, served, min_iou=min_iou)
    assert result.matched == 2
    assert result.unmatched_reference == result.unmatched_exported == 0
    assert result.max_box_error == pytest.approx(offset)
    assert result.max_score_error == 1


@pytest.mark.parametrize("field", ["mAP", "map50", "recall", "per_class_recall"])
@pytest.mark.parametrize("value", [-0.1, 1.1, np.inf, np.nan])
@pytest.mark.parametrize("side", ["native", "exported"])
def test_quality_gate_revalidates_every_metric_on_each_side(
    field: str, value: float, side: str
) -> None:
    baseline = _metrics()
    invalid = baseline.model_copy(
        update={field: {"object": value} if field == "per_class_recall" else value}
    )
    native, exported = (invalid, baseline) if side == "native" else (baseline, invalid)
    assert not quality_gate(native, exported, precision="fp32", reference_detection_count=1)


def test_quality_gate_accepts_perfect_metrics_and_zero_recall_for_one_class() -> None:
    perfect = _metrics(1)
    partial = _metrics().model_copy(update={"per_class_recall": {"found": 1.0, "missed": 0.0}})
    for metrics in (perfect, partial):
        assert quality_gate(metrics, metrics, precision="fp32", reference_detection_count=1)
    assert not quality_gate(_metrics(0), perfect, precision="fp32", reference_detection_count=1)


@pytest.mark.parametrize("detection_count", [0, -1])
def test_quality_gate_requires_observed_reference_detections(detection_count: int) -> None:
    assert not quality_gate(
        _metrics(), _metrics(), precision="fp32", reference_detection_count=detection_count
    )


def test_quality_gate_rejects_unsupported_precision_with_a_diagnostic() -> None:
    with pytest.raises(ValueError, match=r"^Quality gate precision must be fp32 or fp16$"):
        quality_gate(
            _metrics(),
            _metrics(),
            precision=cast(Literal["fp32", "fp16"], "int8"),
            reference_detection_count=1,
        )


@pytest.mark.parametrize(("precision", "tolerance"), [("fp32", 0.001), ("fp16", 0.005)])
@pytest.mark.parametrize(
    ("excess", "accepted"),
    [(-0.1, True), (0, True), (0.5e-12, True), (2e-12, False), (0.001, False)],
)
def test_accuracy_loss_boundary_uses_absolute_roundoff_tolerance(
    precision: Literal["fp32", "fp16"], tolerance: float, excess: float, accepted: bool
) -> None:
    assert quality_gate(
        _metrics(),
        _metrics(0.5 - tolerance - excess),
        precision=precision,
        reference_detection_count=1,
    ) is accepted
