"""Bounded generated checks with independent semantic and durable-state oracles."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
from hypothesis import example, given, settings
from hypothesis import strategies as st

from clearml_yolo.adapters.evaluation.scoring import (
    compute_evaluation,
    filter_invalid_prediction_boxes,
)
from clearml_yolo.adapters.yolo.reinfer import reinfer_split

_LEXICAL = st.sampled_from(["0001", "10", "ёж", "猫", "e\u0301", "é", "001,猫"])
_CONFIDENCE = st.sampled_from([0.0, 0.2, 0.5, 0.700000000000003, 1.0])
_BOUNDS = settings(max_examples=24, deadline=None, derandomize=True, database=None)
_BOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
_PRED_COLUMNS = ["image_name", "instance_label", *_BOX_COLUMNS, "confidence"]


@_BOUNDS
@given(label=_LEXICAL, image=_LEXICAL, confidence=_CONFIDENCE)
@example(label="0001", image="0010", confidence=0.700000000000003)
@example(label="e\u0301", image="é", confidence=0.5)
@example(label="NA", image="NULL", confidence=0.700000000000003)
@example(label="nan", image="None", confidence=0.5)
def test_real_prediction_cache_roundtrip_preserves_lexical_and_float_values(
    label: str, image: str, confidence: float
) -> None:
    with TemporaryDirectory(prefix="cy-quality-cache-", dir=os.environ["CY_HOME"]) as temporary:
        root = Path(temporary)
        path = root / "image.jpg"
        path.write_bytes(b"model effects are replaced")
        truth = pd.DataFrame(
            {
                "image_name": [image],
                "image_path": [str(path)],
                "instance_label": [label],
                "split": ["test"],
            }
        )
        calls: list[list[str]] = []

        def predictor(_weights: object, paths: list[str], **_kwargs: Any) -> pd.DataFrame:
            calls.append(paths)
            return pd.DataFrame([(image, label, 0, 0, 10, 10, confidence)], columns=_PRED_COLUMNS)

        arguments: dict[str, Any] = {
            "conf": 0.001,
            "iou": 0.7,
            "imgsz": 64,
            "batch": 1,
            "device": "cpu",
            "image_name": "name",
            "native_project": root / "native",
            "native_name": "test",
            "predictor": predictor,
            "class_names": lambda _: {0: label},
        }
        output = root / "cache.csv"
        reinfer_split(root / "best.pt", truth, "test", output, **arguments)
        original = output.read_bytes()
        cached, vocabulary = reinfer_split(root / "best.pt", truth, "test", output, **arguments)
        assert calls == [[str(path)]]
        assert output.read_bytes() == original
        assert cached["image_name"].tolist() == [image]
        assert cached["instance_label"].tolist() == [label]
        assert cached["confidence"].tolist() == [confidence]
        assert vocabulary.model_classes == [label]
        assert vocabulary.unknown_to_model == []


@_BOUNDS
@given(
    label=_LEXICAL,
    threshold=_CONFIDENCE,
    detections=st.lists(st.tuples(st.booleans(), _CONFIDENCE), min_size=1, max_size=5),
    invalid=st.booleans(),
)
@example(label="0001", threshold=0.5, detections=[(False, 0.5)], invalid=False)
@example(label="ёж", threshold=0.5, detections=[(True, 0.5)], invalid=True)
def test_fixed_threshold_counts_match_disjoint_scene_reference(
    label: str, threshold: float, detections: list[tuple[bool, float]], invalid: bool
) -> None:
    """Each image has one GT and optionally one exact TP and one disjoint FP."""
    gt_rows = []
    prediction_rows = []
    for index, (detected, confidence) in enumerate(detections):
        name = f"{index:04}"
        gt_rows.append((name, label, 0, 0, 10, 10, "test"))
        if detected:
            prediction_rows.extend(
                [
                    (name, label, 0, 0, 10, 10, confidence),
                    (name, label, 20, 20, 30, 30, confidence),
                ]
            )
        if invalid:
            prediction_rows.append((name, label, 0, 0, 0, 10, 1.0))
    truth = pd.DataFrame(gt_rows, columns=[*_PRED_COLUMNS[:-1], "split"])
    predictions = pd.DataFrame(prediction_rows, columns=_PRED_COLUMNS)
    original = predictions.copy(deep=True)
    valid = filter_invalid_prediction_boxes(predictions)
    computed = compute_evaluation(
        truth,
        valid,
        valid,
        split="test",
        classes=[label],
        thresholds={label: threshold},
        required_classes=[label],
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        ap_method="interp",
        skip_cohen_kappa=True,
    )
    expected_hits = sum(detected and confidence >= threshold for detected, confidence in detections)
    counts = computed.outcome.counts[label]
    assert (counts.tp, counts.fp, counts.fn) == (
        expected_hits,
        expected_hits,
        len(detections) - expected_hits,
    )
    assert computed.thresholds == {label: threshold}
    assert computed.image_names == [f"{index:04}" for index in range(len(detections))]
    assert len(computed.evaluation_payload.ground_truth) == len(detections)
    pd.testing.assert_frame_equal(predictions, original)
