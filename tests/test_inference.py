"""Manifest inference: what reaches ultralytics, and which image each box is attributed to.

The fake YOLO models the behaviour that actually matters and is easy to get wrong: the
source is a ``.txt`` of absolute paths, ``Results`` come back sorted by that path rather
than in the order the caller listed them, and an image ultralytics cannot read simply
never appears among the results.
"""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import numpy as np
import pytest
from loguru import logger

from clearml_yolo.inference import (
    PREDICTION_COLUMNS,
    predict_on_images,
    resolution_of,
)


def _predict(weights: str | Path, paths: list[str], **overrides: Any) -> Any:
    from native_config_helpers import prediction_config

    settings = prediction_config()
    settings.pop("model")
    settings.pop("source")
    return predict_on_images(weights, paths, **(settings | overrides))


NAMES = {0: "person", 1: "dog"}


class _Movable:
    """A numpy array wearing torch's ``.cpu().numpy()``."""

    def __init__(self, values: np.ndarray) -> None:
        self._values = values

    def cpu(self) -> Self:
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
    def __init__(self, path: str, boxes: FakeBoxes | None) -> None:
        # What a manifest source really reports: the absolutised file, not a placeholder.
        self.path = path
        self.boxes = boxes


class FakeYolo:
    """Records every predict call and replays scripted detections the way the loader does.

    The manifest is read back, sorted and filtered exactly as ``LoadImagesAndVideos`` does
    it, so the tests exercise the real ordering and the real skipping.
    """

    last: "FakeYolo | None" = None

    def __init__(self, weights: str) -> None:
        self.weights = weights
        self.names = dict(NAMES)
        self.model = SimpleNamespace(yaml={"nc": 2, "backbone": [[-1, 1, "Conv", [16, 3, 2]]]})
        self.task = "detect"
        self.calls: list[dict[str, Any]] = []
        FakeYolo.last = self

    def predict(self, source: str, **kwargs: Any) -> Iterator[FakeResult]:
        # The manifest lives in a temporary directory that is gone by the time a test
        # looks at the call, so its contents are recorded alongside its path.
        manifest = Path(source).read_text().splitlines()
        self.calls.append({"source": source, "manifest": manifest, **kwargs})
        listed = sorted(manifest)
        return iter(
            [
                FakeResult(path, DETECTIONS.get(Path(path).name))
                for path in listed
                if Path(path).name not in UNREADABLE
            ]
        )


# File name -> the boxes that image's result carries.
DETECTIONS: dict[str, FakeBoxes | None] = {}
# File names ultralytics drops without producing a result at all.
UNREADABLE: set[str] = set()


@pytest.fixture(autouse=True)
def fake_ultralytics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install FakeYolo where the lazy ``from ultralytics.models import YOLO`` finds it."""
    import sys
    import types

    module = types.ModuleType("ultralytics.models")
    module.YOLO = FakeYolo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)

    DETECTIONS.clear()
    UNREADABLE.clear()


def _boxes(*detections: tuple[list[float], float, int]) -> FakeBoxes:
    return FakeBoxes(list(detections))


@pytest.fixture
def checkpoint_recording(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stand in for the checkpoint reader, which would otherwise need a real .pt file."""

    def _record(train_args: dict[str, Any]) -> None:
        import sys
        import types

        module = types.ModuleType("ultralytics.nn.tasks")
        module.torch_safe_load = lambda path: ({"train_args": train_args}, path)  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "ultralytics.nn.tasks", module)

    return _record


def test_inference_requires_configured_resolution(checkpoint_recording: Any) -> None:
    checkpoint_recording({"imgsz": 1280})
    with pytest.raises(ValueError, match="imgsz"):
        resolution_of("best.pt", None)


def test_a_named_resolution_wins_but_is_answered_for(
    checkpoint_recording: Any, logs: list[str]
) -> None:
    """Scoring a model at a scale it was never shown is a real thing to want and a common
    thing to do by accident, so it happens but never quietly."""
    checkpoint_recording({"imgsz": 1280})

    resolution = resolution_of("best.pt", 640)

    assert (resolution.scored_at, resolution.trained_at) == (640, 1280)
    assert resolution.was_trained_elsewhere
    assert any("trained at 1280" in message for message in logs)


def test_the_resolution_pair_carries_both_numbers_into_the_run_record(
    checkpoint_recording: Any,
) -> None:
    """The two places that keep the pair — ClearML and the dev workbook — must say the same
    thing, so the table both render is built once."""
    checkpoint_recording({"imgsz": 1280})

    rows = resolution_of("best.pt", 640).as_table()

    assert dict(zip(rows["parameter"], rows["value"], strict=True)) == {
        "trained at imgsz": "1280",
        "requested inference imgsz": "640",
        "same requested size?": "different requested size; compare the normalized predictor target",
    }


def test_a_checkpoint_that_names_no_resolution_does_not_read_as_agreement(
    checkpoint_recording: Any,
) -> None:
    """Nothing recorded is not the same as the same number, and must not report as one."""
    checkpoint_recording({})

    resolution = resolution_of("best.pt", 640)

    assert resolution.trained_at is None
    assert not resolution.was_trained_elsewhere
    assert "unknown" in resolution.as_table()["value"].iloc[-1]


def test_a_checkpoint_that_names_no_resolution_is_refused(checkpoint_recording: Any) -> None:
    """640 is a plausible enough number to be wrong without ever looking wrong."""
    checkpoint_recording({})

    with pytest.raises(ValueError, match="Set imgsz explicitly"):
        resolution_of("best.pt", None)


def test_each_box_is_attributed_by_path_not_by_position() -> None:
    """Ultralytics sorts a manifest, so results do not arrive in the caller's order; only
    joining on ``Results.path`` keeps every box on the image it was found in."""
    DETECTIONS["000012.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))
    DETECTIONS["000018.png"] = _boxes(([5, 6, 7, 8], 0.8, 1))

    frame = _predict("best.pt", ["dir/000018.png", "dir/000012.png"], device="cpu")

    assert dict(zip(frame["image_name"], frame["instance_label"], strict=True)) == {
        "000012.png": "person",
        "000018.png": "dog",
    }


@pytest.mark.parametrize(
    ("mode", "expected"), [("name", "000012.png"), ("stem", "000012"), ("path", "dir/000012.png")]
)
def test_the_image_name_mode_decides_how_the_join_key_is_spelled(mode: Any, expected: str) -> None:
    """``path`` is the caller's own spelling, not the absolute one the manifest carries."""
    DETECTIONS["000012.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))

    frame = _predict("best.pt", ["dir/000012.png"], image_name=mode, device="cpu")

    assert frame["image_name"].tolist() == [expected]


def test_unknown_image_name_mode_is_rejected_before_native_inference() -> None:
    with pytest.raises(ValueError, match="Unsupported image_name mode"):
        _predict(
            "best.pt",
            ["dir/000012.png"],
            image_name="filename",
            device="cpu",
        )


def test_images_without_detections_contribute_no_rows() -> None:
    DETECTIONS["a.png"] = None
    DETECTIONS["b.png"] = _boxes()

    frame = _predict("best.pt", ["a.png", "b.png"], device="cpu")

    assert frame.empty
    assert list(frame.columns) == PREDICTION_COLUMNS


def test_the_whole_run_is_one_predict_call_with_batch_forwarded() -> None:
    """A manifest source honours ``batch``, so there is nothing left to chunk by hand."""
    for index in range(5):
        DETECTIONS[f"{index}.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))

    frame = _predict("best.pt", [f"{index}.png" for index in range(5)], batch=2, device="cpu")

    calls = FakeYolo.last.calls  # type: ignore[union-attr]
    assert len(calls) == 1
    assert calls[0]["batch"] == 2
    assert len(frame) == 5


def test_ultralytics_is_handed_a_txt_manifest_of_absolute_paths() -> None:
    """The ``.txt`` suffix is what routes the source to the loader that honours ``batch``
    and reports real paths; absolute entries keep the join off the manifest's own parent."""
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))

    _predict("best.pt", ["dir/a.png", "/tmp/b.png"], device="cpu")

    call = FakeYolo.last.calls[0]  # type: ignore[union-attr]
    assert Path(call["source"]).suffix == ".txt"
    assert call["manifest"] == [str(Path("dir/a.png").absolute()), "/tmp/b.png"]


def test_an_image_ultralytics_could_not_read_is_refused_not_dropped() -> None:
    """A skipped image would otherwise shrink the scored set and read as a recall drop."""
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))
    UNREADABLE.add("broken.png")

    with pytest.raises(ValueError, match="no result for 1 of 2 images"):
        _predict("best.pt", ["a.png", "broken.png"], device="cpu")


def test_default_prediction_settings_reach_ultralytics() -> None:
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))
    _predict("best.pt", ["a.png"], device="0")
    assert FakeYolo.last is not None
    call = FakeYolo.last.calls[0]
    assert call["quantize"] is None
    assert call["compile"] is True
    assert call["rect"] is True
    assert call["stream"] is True


@pytest.mark.parametrize("quantize", [32, "fp32"])
def test_explicit_prediction_settings_reach_ultralytics(quantize: int | str) -> None:
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))
    _predict(
        "best.pt",
        ["a.png"],
        conf=0.25,
        iou=0.5,
        imgsz=1280,
        device="0",
        quantize=quantize,
        compile=False,
        rect=False,
    )
    assert FakeYolo.last is not None
    call = FakeYolo.last.calls[0]
    assert (call["conf"], call["iou"], call["imgsz"], call["device"]) == (0.25, 0.5, 1280, "0")
    assert call["quantize"] == quantize
    assert call["quantize"] != 16
    assert call["compile"] is False
    assert call["rect"] is False
    assert call["stream"] is True


def test_a_batch_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="batch"):
        _predict("best.pt", ["a.png"], batch=0)


def test_no_images_is_an_empty_frame_rather_than_a_crash() -> None:
    """Ultralytics raises FileNotFoundError on an empty manifest; an empty split must not."""
    frame = _predict("best.pt", [], device="cpu")

    assert frame.empty
    assert list(frame.columns) == PREDICTION_COLUMNS


@pytest.fixture
def logs() -> Iterator[list[str]]:
    messages: list[str] = []

    def sink(message: Any) -> None:
        messages.append(message.record["message"])

    sink_id = logger.add(sink, level="INFO")
    yield messages
    logger.remove(sink_id)


def test_the_run_says_what_it_scored(logs: list[str]) -> None:
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0), ([5, 6, 7, 8], 0.7, 1))

    _predict("best.pt", ["a.png"], device="cpu")

    assert "Predicted 2 boxes over 1 images" in logs


def test_the_weights_path_is_forwarded_as_given(tmp_path: Path) -> None:
    checkpoint = tmp_path / "best.pt"
    DETECTIONS["a.png"] = _boxes(([1, 2, 3, 4], 0.9, 0))

    _predict(checkpoint, ["a.png"], device="cpu")

    assert FakeYolo.last.weights == str(checkpoint)  # type: ignore[union-attr]


def test_rectangular_native_resolution_is_preserved(checkpoint_recording: Any) -> None:
    checkpoint_recording({"imgsz": 640})
    result = resolution_of("best.pt", [320, 640])
    assert result.scored_at == [320, 640]


def test_explicit_manifest_persists_for_native_yaml_replay(tmp_path: Path) -> None:
    frame = _predict("best.pt", ["a.png"], device="cpu", manifest_dir=tmp_path / "inputs")
    manifest = Path(frame.attrs["effective_args"]["source"])
    assert manifest.is_file()
    assert manifest.read_text() == str(Path("a.png").absolute())
    assert frame.attrs["effective_args"]["model"] == "best.pt"
    assert frame.attrs["effective_args"]["mode"] == "predict"


def test_missing_native_settings_do_not_fall_back() -> None:
    with pytest.raises(ValueError, match="ultralytics_predict"):
        predict_on_images("best.pt", ["a.png"])


def test_native_normalization_is_separate_from_requested_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from native_config_helpers import prediction_config

    original = FakeYolo.predict

    def normalized(self: FakeYolo, source: str, **kwargs: Any) -> Iterator[FakeResult]:
        self.predictor = SimpleNamespace(  # type: ignore[attr-defined]
            args=SimpleNamespace(**kwargs), imgsz=[928, 928], save_dir="native/predict"
        )
        return original(self, source, **kwargs)

    monkeypatch.setattr(FakeYolo, "predict", normalized)
    settings = prediction_config(imgsz=906, compile=True, nms=True)
    for key in ("model", "source"):
        settings.pop(key, None)
    frame = predict_on_images("best.pt", ["a.png"], **settings)
    assert frame.attrs["requested_args"]["imgsz"] == 906
    assert frame.attrs["normalized_imgsz"] == [928, 928]
    assert FakeYolo.last is not None
    assert FakeYolo.last.calls[0]["compile"] is True
    assert FakeYolo.last.calls[0]["nms"] is True


@pytest.mark.parametrize("task", ["segment", "pose", "classify", "obb"])
def test_non_detection_checkpoint_fails_before_prediction(
    monkeypatch: pytest.MonkeyPatch, task: str
) -> None:
    original = FakeYolo.__init__

    def initialize(self: FakeYolo, weights: str) -> None:
        original(self, weights)
        self.task = task

    monkeypatch.setattr(FakeYolo, "__init__", initialize)
    with pytest.raises(ValueError, match="detection model"):
        _predict("wrong.pt", ["a.png"])


def test_inference_retains_checkpoint_design(tmp_path: Path) -> None:
    frame = _predict("best.pt", [str(tmp_path / "empty.jpg")])
    assert frame.attrs["checkpoint_design"]["nc"] == 2
