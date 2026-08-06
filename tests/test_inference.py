"""Batched inference: what runs on the GPU, and which image each box is attributed to.

The ultralytics call itself is the only part not exercised here. Everything around it is,
through a fake ``YOLO`` that records the settings it was handed and yields results in
whatever order the test asks for — which is the point, because ultralytics sorts a list
source and does not return results in the order they were passed.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from loguru import logger

from clearml_yolo.inference import PREDICTION_COLUMNS, predict_on_images, uses_half_precision

NAMES = {0: "person", 1: "dog"}


class FakeBoxes:
    """The three tensors ``predict_on_images`` reads off a Results object."""

    def __init__(self, detections: list[tuple[list[float], float, int]]) -> None:
        self.xyxy = _Movable(np.array([box for box, _, _ in detections], dtype=float))
        self.conf = _Movable(np.array([score for _, score, _ in detections], dtype=float))
        self.cls = _Movable(np.array([index for _, _, index in detections], dtype=float))
        self._length = len(detections)

    def __len__(self) -> int:
        return self._length


class _Movable:
    """A numpy array wearing torch's ``.cpu().numpy()``."""

    def __init__(self, values: np.ndarray) -> None:
        self._values = values

    def cpu(self) -> _Movable:
        return self

    def numpy(self) -> np.ndarray:
        return self._values


class FakeResult:
    def __init__(self, path: str, boxes: FakeBoxes | None) -> None:
        self.path = path
        self.boxes = boxes


class FakeYolo:
    """Records what predict was asked for, and replays a scripted set of results."""

    last: FakeYolo | None = None

    def __init__(self, weights: str) -> None:
        self.weights = weights
        self.names = dict(NAMES)
        self.settings: dict[str, Any] = {}
        FakeYolo.last = self

    def predict(self, **kwargs: Any) -> Iterator[FakeResult]:
        self.settings = kwargs
        return iter(RESULTS)


RESULTS: list[FakeResult] = []


@pytest.fixture(autouse=True)
def fake_ultralytics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install FakeYolo where the lazy ``from ultralytics.models import YOLO`` finds it."""
    import sys
    import types

    module = types.ModuleType("ultralytics.models")
    module.YOLO = FakeYolo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    RESULTS.clear()


def _detected(path: str, *detections: tuple[list[float], float, int]) -> FakeResult:
    return FakeResult(str(Path(path).absolute()), FakeBoxes(list(detections)))


def test_boxes_follow_the_result_path_not_the_input_order() -> None:
    """Ultralytics sorts a list source, so zipping against the input order misattributes.

    Every box here would land on the wrong image under a positional zip.
    """
    RESULTS.extend(
        [
            _detected("b.jpg", ([1, 2, 3, 4], 0.9, 1)),
            _detected("a.jpg", ([5, 6, 7, 8], 0.8, 0)),
        ]
    )

    frame = predict_on_images("best.pt", ["a.jpg", "b.jpg"], device="cpu")

    by_image = dict(zip(frame["image_name"], frame["instance_label"], strict=True))
    assert by_image == {"b.jpg": "dog", "a.jpg": "person"}


def test_relative_paths_still_name_the_image_the_caller_passed() -> None:
    """Ultralytics reports absolute paths; the ground truth joins on what was passed in."""
    RESULTS.append(_detected("images/a.jpg", ([1, 2, 3, 4], 0.9, 0)))

    frame = predict_on_images("best.pt", ["images/a.jpg"], image_name="path", device="cpu")

    assert frame["image_name"].tolist() == ["images/a.jpg"]


def test_images_without_detections_contribute_no_rows() -> None:
    RESULTS.extend([FakeResult(str(Path("a.jpg").absolute()), None), _detected("b.jpg")])

    frame = predict_on_images("best.pt", ["a.jpg", "b.jpg"], device="cpu")

    assert frame.empty
    assert list(frame.columns) == PREDICTION_COLUMNS


def test_the_batch_size_reaches_ultralytics() -> None:
    """The whole point: without this ultralytics builds a batch-of-one dataloader."""
    RESULTS.append(_detected("a.jpg", ([1, 2, 3, 4], 0.9, 0)))

    predict_on_images("best.pt", ["a.jpg"], batch=32, imgsz=1280, conf=0.25, device="0")

    settings = FakeYolo.last.settings  # type: ignore[union-attr]
    assert settings["batch"] == 32
    assert settings["imgsz"] == 1280
    assert settings["conf"] == 0.25
    assert settings["stream"] is True


def test_half_precision_is_on_for_a_card_and_off_for_the_cpu() -> None:
    RESULTS.append(_detected("a.jpg", ([1, 2, 3, 4], 0.9, 0)))
    predict_on_images("best.pt", ["a.jpg"], device="0")
    assert FakeYolo.last.settings["half"] is True  # type: ignore[union-attr]

    RESULTS.clear()
    RESULTS.append(_detected("a.jpg", ([1, 2, 3, 4], 0.9, 0)))
    predict_on_images("best.pt", ["a.jpg"], device="cpu")
    assert FakeYolo.last.settings["half"] is False  # type: ignore[union-attr]


def test_an_explicit_half_wins_over_the_device_default() -> None:
    """FP16 shifts confidences, so a run that needs the old numbers must be able to opt out."""
    RESULTS.append(_detected("a.jpg", ([1, 2, 3, 4], 0.9, 0)))

    predict_on_images("best.pt", ["a.jpg"], device="0", half=False)

    assert FakeYolo.last.settings["half"] is False  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("device", "expected"),
    [("0", True), ("0,1", True), ("cuda:0", True), ("cpu", False), ("mps", False)],
)
def test_which_devices_can_run_half_precision(device: str, expected: bool) -> None:
    assert uses_half_precision(device) is expected


def test_a_batch_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="batch must be >= 1"):
        predict_on_images("best.pt", ["a.jpg"], batch=0)


@pytest.fixture
def warnings_logged() -> Iterator[list[str]]:
    messages: list[str] = []

    def sink(message: Any) -> None:
        if message.record["level"].name == "WARNING":
            messages.append(message.record["message"])

    sink_id = logger.add(sink, level="WARNING")
    yield messages
    logger.remove(sink_id)


def test_images_ultralytics_dropped_are_reported(warnings_logged: list[str]) -> None:
    """Ultralytics silently skips sources it does not recognise as images, which would
    otherwise surface much later as unexplained missed detections."""
    RESULTS.append(_detected("a.jpg", ([1, 2, 3, 4], 0.9, 0)))

    predict_on_images("best.pt", ["a.jpg", "notes.txt"], device="cpu")

    assert warnings_logged == ["Asked for 2 images but ultralytics returned 1; the difference "
                               "was not recognised as image files"]
