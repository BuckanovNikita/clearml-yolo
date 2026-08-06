"""Batched inference: what reaches ultralytics, and which image each box is attributed to.

The fake YOLO models the behaviour that actually matters and is easy to get wrong: a list
source arrives as decoded arrays, results come back in input order, and ``Results.path`` is
a generic ``imageN.jpg`` rather than the file — so anything keying on it silently produces
image names that join to nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from loguru import logger

from clearml_yolo import inference as inference_module
from clearml_yolo.inference import PREDICTION_COLUMNS, predict_on_images
from clearml_yolo.inference import _read_image as read_image  # bound before the stub lands

NAMES = {0: "person", 1: "dog"}


class _Movable:
    """A numpy array wearing torch's ``.cpu().numpy()``."""

    def __init__(self, values: np.ndarray) -> None:
        self._values = values

    def cpu(self) -> _Movable:
        return self

    def numpy(self) -> np.ndarray:
        return self._values


class FakeBoxes:
    """The three tensors predict_on_images reads off a Results object."""

    def __init__(self, detections: list[tuple[list[float], float, int]]) -> None:
        self.xyxy = _Movable(np.array([box for box, _, _ in detections], dtype=float))
        self.conf = _Movable(np.array([score for _, score, _ in detections], dtype=float))
        self.cls = _Movable(np.array([index for _, _, index in detections], dtype=float))
        self._length = len(detections)

    def __len__(self) -> int:
        return self._length


class FakeResult:
    def __init__(self, index: int, boxes: FakeBoxes | None) -> None:
        # What ultralytics really reports for a list source: the position, not the file.
        self.path = f"image{index}.jpg"
        self.boxes = boxes


class FakeYolo:
    """Records every predict call and replays scripted detections in input order."""

    last: FakeYolo | None = None

    def __init__(self, weights: str) -> None:
        self.weights = weights
        self.names = dict(NAMES)
        self.calls: list[dict[str, Any]] = []
        FakeYolo.last = self

    def predict(self, source: list[Any], **kwargs: Any) -> Iterator[FakeResult]:
        self.calls.append({"source": source, **kwargs})
        start = sum(len(call["source"]) for call in self.calls[:-1])
        positions = range(start, start + len(source))
        return iter([FakeResult(index, DETECTIONS.get(index)) for index in positions])


# Position in the input list -> the boxes that image's result carries.
DETECTIONS: dict[int, FakeBoxes | None] = {}
DECODED: list[str] = []


@pytest.fixture(autouse=True)
def fake_ultralytics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install FakeYolo where the lazy ``from ultralytics.models import YOLO`` finds it, and
    replace the decoder so no test needs a real image on disk."""
    import sys
    import types

    module = types.ModuleType("ultralytics.models")
    module.YOLO = FakeYolo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)

    def read(path: str) -> np.ndarray:
        DECODED.append(path)
        return np.zeros((4, 4, 3), dtype=np.uint8)

    monkeypatch.setattr(inference_module, "_read_image", read)
    DETECTIONS.clear()
    DECODED.clear()


def _boxes(*detections: tuple[list[float], float, int]) -> FakeBoxes:
    return FakeBoxes(list(detections))


def test_each_image_keeps_the_name_the_caller_passed() -> None:
    """Results.path is 'imageN.jpg' for a list source, so anything keyed on it joins to
    nothing downstream; the pairing has to be positional."""
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))
    DETECTIONS[1] = _boxes(([5, 6, 7, 8], 0.8, 1))

    frame = predict_on_images("best.pt", ["dir/000012.png", "dir/000018.png"], device="cpu")

    assert dict(zip(frame["image_name"], frame["instance_label"], strict=True)) == {
        "000012.png": "person",
        "000018.png": "dog",
    }


@pytest.mark.parametrize(
    ("mode", "expected"), [("name", "000012.png"), ("stem", "000012"), ("path", "dir/000012.png")]
)
def test_the_image_name_mode_decides_how_the_join_key_is_spelled(mode: Any, expected: str) -> None:
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))

    frame = predict_on_images("best.pt", ["dir/000012.png"], image_name=mode, device="cpu")

    assert frame["image_name"].tolist() == [expected]


def test_images_without_detections_contribute_no_rows() -> None:
    DETECTIONS[0] = None
    DETECTIONS[1] = _boxes()

    frame = predict_on_images("best.pt", ["a.png", "b.png"], device="cpu")

    assert frame.empty
    assert list(frame.columns) == PREDICTION_COLUMNS


def test_the_batch_is_the_chunk_because_ultralytics_ignores_its_own_batch_argument() -> None:
    """A list source becomes one forward pass of the whole list, so chunking is the only
    batch-size control there is."""
    for index in range(5):
        DETECTIONS[index] = _boxes(([1, 2, 3, 4], 0.9, 0))

    predict_on_images("best.pt", [f"{index}.png" for index in range(5)], batch=2, device="cpu")

    calls = FakeYolo.last.calls  # type: ignore[union-attr]
    assert [len(call["source"]) for call in calls] == [2, 2, 1]
    assert "batch" not in calls[0], "passing batch= would imply it does something"


def test_ultralytics_is_handed_decoded_arrays_not_paths() -> None:
    """Decoding happens here, off the main thread, because ultralytics does it inline."""
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))

    predict_on_images("best.pt", ["dir/a.png"], device="cpu")

    source = FakeYolo.last.calls[0]["source"]  # type: ignore[union-attr]
    assert [type(image) for image in source] == [np.ndarray]
    assert DECODED == ["dir/a.png"]


def test_inference_settings_reach_ultralytics() -> None:
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))

    predict_on_images("best.pt", ["a.png"], conf=0.25, iou=0.5, imgsz=1280, device="0")

    call = FakeYolo.last.calls[0]  # type: ignore[union-attr]
    assert (call["conf"], call["iou"], call["imgsz"], call["device"]) == (0.25, 0.5, 1280, "0")
    assert call["stream"] is True
    # Half precision is off unless asked for: the network is a tenth of the wall clock here,
    # so FP16 measured slower while still moving every calibrated threshold.
    assert "half" not in call


def test_half_precision_can_still_be_asked_for() -> None:
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))

    predict_on_images("best.pt", ["a.png"], device="0", half=True)

    assert FakeYolo.last.calls[0]["half"] is True  # type: ignore[union-attr]


def test_a_batch_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="batch must be >= 1"):
        predict_on_images("best.pt", ["a.png"], batch=0)


def test_no_images_is_an_empty_frame_rather_than_a_crash() -> None:
    frame = predict_on_images("best.pt", [], device="cpu")

    assert frame.empty
    assert list(frame.columns) == PREDICTION_COLUMNS


def test_an_undecodable_image_names_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """cv2.imread returns None rather than raising, which would otherwise surface much
    later as a np.stack crash naming nothing."""
    import sys
    import types

    fake_cv2 = types.ModuleType("cv2")
    fake_cv2.imread = lambda path: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    # The module attribute is stubbed for every other test; this one wants the real reader.
    with pytest.raises(ValueError, match="Cannot decode broken.png"):
        read_image("broken.png")


@pytest.fixture
def logs() -> Iterator[list[str]]:
    messages: list[str] = []

    def sink(message: Any) -> None:
        messages.append(message.record["message"])

    sink_id = logger.add(sink, level="INFO")
    yield messages
    logger.remove(sink_id)


def test_the_run_says_what_it_scored(logs: list[str]) -> None:
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0), ([5, 6, 7, 8], 0.7, 1))

    predict_on_images("best.pt", ["a.png"], device="cpu")

    assert "Predicted 2 boxes over 1 images" in logs


def test_the_weights_path_is_forwarded_as_given(tmp_path: Path) -> None:
    checkpoint = tmp_path / "best.pt"
    DETECTIONS[0] = _boxes(([1, 2, 3, 4], 0.9, 0))

    predict_on_images(checkpoint, ["a.png"], device="cpu")

    assert FakeYolo.last.weights == str(checkpoint)  # type: ignore[union-attr]
