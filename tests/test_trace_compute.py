"""Compute traces cover lazy inference and retain exact scientific results."""

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd
import pytest
from loguru import logger

from clearml_yolo.adapters.evaluation import scoring
from clearml_yolo.adapters.yolo.inference import predict_on_images
from native_config_helpers import prediction_config


def test_inference_span_covers_stream_consumption_and_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda record: messages.append(str(record)), level="TRACE")
    error = RuntimeError("lazy inference failed")

    class Model:
        task = "detect"

        def __init__(self, _: object) -> None:
            self.names: dict[int, str] = {}

        def predict(self, **_: Any) -> Iterator[object]:
            yield from ()
            assert any("START yolo.inference.stream" in line for line in messages)
            assert not any("DONE yolo.inference.stream" in line for line in messages)
            raise error

    models = ModuleType("ultralytics.models")
    models.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", models)
    settings = prediction_config()
    settings.pop("model")
    settings.pop("source")
    try:
        with pytest.raises(RuntimeError) as raised:
            predict_on_images("model.pt", [str(tmp_path / "image.png")], **settings)
    finally:
        logger.remove(sink)
    assert raised.value is error
    assert any("DONE yolo.model.load" in line for line in messages)
    assert any("FAILED yolo.inference.stream" in line for line in messages)


def test_calibration_trace_preserves_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    columns = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
    truth = pd.DataFrame([("image.png", "cat", 0, 0, 10, 10)], columns=columns)
    truth["split"] = "val"
    predictions = pd.DataFrame(
        [("image.png", "cat", 0, 0, 10, 10, 0.8)], columns=[*columns, "confidence"]
    )
    def calibrate() -> dict[str, float]:
        return scoring.calibrate_thresholds(
            truth, predictions, calibration_split="val", classes=["cat"],
            iou_threshold=0.5, matching_strategy="greedy", confidence_optimization="per_class",
        )

    expected = calibrate()
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda record: messages.append(str(record)), level="TRACE")
    try:
        actual = calibrate()
    finally:
        logger.remove(sink)
    assert actual == expected
    for operation in ("evaluation.calibration.match", "evaluation.calibration.optimize"):
        assert any(f"START {operation}" in line for line in messages)
        assert any(f"DONE {operation}" in line for line in messages)


def test_reinfer_cache_hit_is_distinct_from_native_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from test_comparison_reinfer import RecordingPredictor, _explode, _reinfer

    image = tmp_path / "image.jpg"
    image.write_bytes(b"fixture")
    truth = pd.DataFrame(
        [(str(image), image.name, "person", "test", 0.0, 0.0, 10.0, 10.0)],
        columns=[
            "image_path",
            "image_name",
            "instance_label",
            "split",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
        ],
    )
    output = tmp_path / "predictions.csv"
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda record: messages.append(str(record)), level="TRACE")
    try:
        fresh, _ = _reinfer(truth, output, RecordingPredictor())
        assert any("DONE yolo.cache.miss.inference" in line for line in messages)
        messages.clear()
        cached, _ = _reinfer(truth, output, _explode)
    finally:
        logger.remove(sink)
    pd.testing.assert_frame_equal(fresh, cached)
    assert any("DONE yolo.cache.hit" in line for line in messages)
    assert not any("yolo.cache.miss.inference" in line for line in messages)
