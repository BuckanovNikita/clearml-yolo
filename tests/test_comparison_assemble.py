"""Assembling two scored splits into the frame both reports read.

The tests lean on the contracts the consumers pin: the column set in
``comparison/workbook.py`` and the pooled/BH conventions in ``clearml_report.py``.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.clearml_report import COMPARED_METRICS, POOLED_COLUMN
from clearml_yolo.comparison.assemble import (
    DEGRADED,
    IMPROVED,
    NOT_SIGNIFICANT,
    UNKNOWN_TO_BASELINE,
    UNKNOWN_TO_BOTH,
    ComparisonTables,
    build_comparison_rows,
)
from clearml_yolo.comparison.scoring import ClassCounts, SplitOutcome
from clearml_yolo.comparison.workbook import COMPARISON_COLUMNS, write_comparison_workbook


def _settled(**overrides: Any) -> Any:
    """Inference settings with every "decide this for me" already decided."""
    from clearml_yolo.tasks.compare import SettledInference

    return SettledInference(
        conf=0.001,
        iou=0.7,
        imgsz=640,
        batch=16,
        device=None,
        quantize=32,
        image_name="name",
        reuse_existing=True,
    ).model_copy(update=overrides)


CLASSES = ["car", "van"]
IMAGES = [f"img{index}.png" for index in range(40)]


def _outcome(detected: dict[str, list[bool]], correct: dict[str, list[bool]]) -> SplitOutcome:
    """Build a scored split from per-class detected/true-positive flags.

    One ground-truth box and one prediction per image per class keeps the bootstrap's
    per-image resampling meaningful while staying readable.
    """
    counts: dict[str, ClassCounts] = {}
    gt_rows: list[dict[str, object]] = []
    pred_rows: list[dict[str, object]] = []
    index = 0

    for class_name in CLASSES:
        flags = detected[class_name]
        hits = correct[class_name]
        for image, is_detected, is_tp in zip(IMAGES, flags, hits, strict=True):
            gt_rows.append(
                {
                    "gt_index": index,
                    "image_name": image,
                    "instance_label": class_name,
                    "detected": is_detected,
                }
            )
            pred_rows.append(
                {
                    "pred_index": index,
                    "image_name": image,
                    "instance_label": class_name,
                    "is_tp": is_tp,
                }
            )
            index += 1
        counts[class_name] = ClassCounts(
            tp=sum(hits),
            fp=len(hits) - sum(hits),
            fn=len(flags) - sum(flags),
        )

    return SplitOutcome(
        counts=counts,
        gt_status=pd.DataFrame(gt_rows),
        pred_status=pd.DataFrame(pred_rows),
    )


def _flags(per_class: dict[str, int]) -> dict[str, list[bool]]:
    """``count`` leading True flags per class, over the fixed image list."""
    return {
        name: [index < count for index in range(len(IMAGES))]
        for name, count in per_class.items()
    }


def _tables(
    baseline_hits: dict[str, int],
    candidate_hits: dict[str, int],
    **kwargs: Any,
) -> ComparisonTables:
    baseline = _outcome(_flags(baseline_hits), _flags(baseline_hits))
    candidate = _outcome(_flags(candidate_hits), _flags(candidate_hits))
    return build_comparison_rows(
        baseline,
        candidate,
        thresholds_baseline={"car": 0.3, "van": 0.4},
        thresholds_candidate={"car": 0.35, "van": 0.45},
        images=IMAGES,
        iterations=200,
        seed=0,
        **kwargs,
    )


def test_every_column_the_workbook_pins_is_present() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})

    required = {POOLED_COLUMN, *(name for name, _ in COMPARISON_COLUMNS)}
    assert required <= set(tables.rows.columns)


def test_the_workbook_accepts_the_assembled_frame(tmp_path: Path) -> None:
    """The two halves have never met before; this is the join."""
    tables = _tables({"car": 20, "van": 20}, {"car": 34, "van": 20})

    destination = tmp_path / "comparison.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, destination)

    assert destination.exists()


def test_exactly_one_pooled_row_and_it_sits_outside_the_family() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})
    rows = tables.rows

    pooled = rows[rows[POOLED_COLUMN].astype(bool)]
    assert len(pooled) == 1
    # Folding the pooled summary into the family would count the same evidence twice.
    assert math.isnan(float(pooled["precision_p_bh"].iloc[0]))
    assert math.isnan(float(pooled["recall_p_bh"].iloc[0]))


def test_declared_family_size_matches_the_adjusted_p_values() -> None:
    """clearml_report warns loudly when these disagree, so they must not."""
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 25})
    rows = tables.rows

    per_class = rows[~rows[POOLED_COLUMN].astype(bool)]
    adjusted = sum(
        int(pd.to_numeric(per_class[metric.adjusted_p_column], errors="coerce").notna().sum())
        for metric in COMPARED_METRICS
    )
    assert tables.methodology["family_size"] == adjusted


def test_a_large_recall_gain_is_called_an_improvement() -> None:
    tables = _tables({"car": 4, "van": 20}, {"car": 36, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["recall_delta"] > 0
    assert car["recall_verdict"] == IMPROVED


def test_a_large_recall_loss_is_called_a_degradation() -> None:
    tables = _tables({"car": 36, "van": 20}, {"car": 4, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["recall_delta"] < 0
    assert car["recall_verdict"] == DEGRADED


def test_an_identical_model_is_never_called_changed() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 20, "van": 20})
    rows = tables.rows

    assert set(rows["precision_verdict"]) == {NOT_SIGNIFICANT}
    assert set(rows["recall_verdict"]) == {NOT_SIGNIFICANT}


def test_a_class_the_baseline_cannot_predict_is_excluded_not_scored() -> None:
    """A model that never heard of a class has no recall on it, not a recall of zero."""
    tables = _tables(
        {"car": 20, "van": 20},
        {"car": 20, "van": 20},
        baseline_classes={"car"},
        candidate_classes={"car", "van"},
    )

    excluded = tables.excluded
    assert list(excluded["class_name"]) == ["van"]
    assert list(excluded["reason"]) == [UNKNOWN_TO_BASELINE]
    assert "van" not in set(tables.rows["class_name"])


def test_a_class_neither_model_knows_is_not_blamed_on_the_new_one() -> None:
    """A labelling gap is not a difference between the models; saying so misdirects."""
    tables = _tables(
        {"car": 20, "van": 20},
        {"car": 20, "van": 20},
        baseline_classes={"car"},
        candidate_classes={"car"},
    )

    assert list(tables.excluded["reason"]) == [UNKNOWN_TO_BOTH]


def test_the_pooled_row_is_judged_on_its_own_p_value() -> None:
    """It sits outside the BH family, but "not significant" beside a large delta lies."""
    tables = _tables({"car": 4, "van": 4}, {"car": 36, "van": 36})
    rows = tables.rows

    pooled = rows[rows[POOLED_COLUMN].astype(bool)].iloc[0]
    assert pooled["recall_delta"] > 0
    assert pooled["recall_verdict"] == IMPROVED


def test_nothing_comparable_is_an_error_rather_than_an_empty_report() -> None:
    with pytest.raises(ValueError, match="No class can be compared"):
        _tables(
            {"car": 20, "van": 20},
            {"car": 20, "van": 20},
            baseline_classes=set(),
            candidate_classes=set(),
        )


def test_each_checkpoint_gets_its_own_prediction_cache(tmp_path: Path) -> None:
    """Two comparisons in one directory must not score each other's detections.

    Keyed on the role alone, a rerun reused the previous run's predictions for whatever
    checkpoint it was now given.
    """
    from clearml_yolo.tasks.compare import SettledInference, _prediction_cache

    settings = _settled(device="0")
    first = tmp_path / "a.pt"
    second = tmp_path / "b.pt"
    first.write_bytes(b"one")
    second.write_bytes(b"two-different-length")

    def cache(weights: Path, inference: SettledInference = settings) -> Path:
        return _prediction_cache(tmp_path, "baseline", "test", weights, inference)

    assert cache(first) != cache(second)
    # The same checkpoint must still hit its cache, or nothing is ever reused.
    assert cache(first) == cache(first)
    # A retrained checkpoint at an unchanged path is a different model.
    before = cache(first)
    first.write_bytes(b"retrained, quite different")
    assert cache(first) != before


def test_a_cache_is_not_reused_across_inference_settings(tmp_path: Path) -> None:
    """Predictions taken at one confidence, resolution or precision are not the same boxes.

    The cache survives a rerun, so without the settings in its key a comparison could score
    one model's detections against the other's taken at a different operating point — a
    warm FP32 cache against fresh FP16 detections, say.
    """
    from clearml_yolo.tasks.compare import _prediction_cache

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"weights")
    # A device is named so the FP16 decision does not depend on the test machine's cards.
    baseline = _settled(device="0")

    for changed in (
        baseline.model_copy(update={"conf": 0.25}),
        baseline.model_copy(update={"iou": 0.5}),
        baseline.model_copy(update={"imgsz": 1280}),
        baseline.model_copy(update={"device": "cpu"}),
        # Ultralytics letterboxes per batch according to whether that batch's images
        # share a shape, so which batch an image travelled in decides its geometry.
        baseline.model_copy(update={"batch": 32}),
    ):
        assert _prediction_cache(tmp_path, "baseline", "test", checkpoint, changed) != (
            _prediction_cache(tmp_path, "baseline", "test", checkpoint, baseline)
        )


def test_comparing_a_model_against_itself_is_refused(tmp_path: Path) -> None:
    """Two lookups can land on one task; every delta is then zero, which reads as a result."""
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")
    same = ModelRef(source="local", weights=checkpoint, thresholds={"car": 0.4})
    (tmp_path / "gt.csv").write_text("image_name,split\na.png,test\n", encoding="utf-8")

    with pytest.raises(ValueError, match="same checkpoint"):
        compare(
            baseline_model=same,
            candidate_model=same.model_copy(),
            ground_truth=tmp_path / "gt.csv",
            output_dir=tmp_path / "out",
            clearml=ClearMLConfig(enabled=False),
            inference=InferenceConfig(device="cpu"),
        )


def test_thresholds_are_carried_through_per_model() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["threshold_baseline"] == pytest.approx(0.3)
    assert car["threshold_candidate"] == pytest.approx(0.35)
