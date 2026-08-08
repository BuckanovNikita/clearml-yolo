"""Re-inference must score the current split's own images, or fail loudly."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, override

import pandas as pd
import pytest
from loguru import logger

from clearml_yolo.comparison.reinfer import VocabularyReport, reinfer_split

PREDICTION_COLUMNS = [
    "image_name",
    "instance_label",
    "confidence",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
]

COCO_NAMES = {0: "person", 1: "dog", 2: "umbrella"}


class RecordingPredictor:
    """Stands in for ``predict_on_images`` so the logic is testable without a GPU."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], dict[str, Any]]] = []

    def __call__(self, weights: Any, image_paths: list[str], **kwargs: Any) -> pd.DataFrame:
        self.calls.append((str(weights), list(image_paths), kwargs))
        rows = [
            {
                "image_name": Path(path).name,
                "instance_label": "person",
                "confidence": 0.9,
                "bbox_x_tl": 1.0,
                "bbox_y_tl": 2.0,
                "bbox_x_br": 3.0,
                "bbox_y_br": 4.0,
            }
            for path in image_paths
        ]
        return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)


class NumericNamePredictor(RecordingPredictor):
    """Emits COCO-style numeric stems, which a naive CSV reload turns into integers."""

    @override
    def __call__(self, weights: Any, image_paths: list[str], **kwargs: Any) -> pd.DataFrame:
        frame = super().__call__(weights, image_paths, **kwargs)
        return frame.assign(image_name=["000000000009", "000000000025"][: len(frame)])


def _explode(weights: Any, image_paths: list[str], **kwargs: Any) -> pd.DataFrame:
    raise AssertionError("inference must not run when a cached prediction file is reused")


def _names(weights: str | Path) -> dict[int, str]:
    return dict(COCO_NAMES)


def _write_images(directory: Path, names: list[str]) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / name for name in names]
    for path in paths:
        path.write_bytes(b"not-a-real-jpeg")
    return paths


@pytest.fixture
def ground_truth(tmp_path: Path) -> pd.DataFrame:
    """Two test images and one train image, each split with its own distinct files."""
    test_images = _write_images(tmp_path / "images" / "test", ["a.jpg", "b.jpg"])
    train_images = _write_images(tmp_path / "images" / "train", ["c.jpg"])
    rows = [
        (test_images[0], "person", "test"),
        (test_images[0], "umbrella", "test"),
        (test_images[1], "dog", "test"),
        (train_images[0], "forklift", "train"),
    ]
    return pd.DataFrame(
        [
            {
                "image_name": path.name,
                "image_path": str(path),
                "instance_label": label,
                "bbox_x_tl": 0.0,
                "bbox_y_tl": 0.0,
                "bbox_x_br": 10.0,
                "bbox_y_br": 10.0,
                "split": split,
            }
            for path, label, split in rows
        ]
    )


@pytest.fixture
def info_logs() -> Iterator[list[str]]:
    messages: list[str] = []

    def sink(message: Any) -> None:
        if message.record["level"].name == "INFO":
            messages.append(message.record["message"])

    sink_id = logger.add(sink, level="INFO")
    yield messages
    logger.remove(sink_id)


def _reinfer(
    ground_truth: pd.DataFrame,
    output: Path,
    predictor: Any,
    *,
    split: str = "test",
    reuse_existing: bool = True,
) -> tuple[pd.DataFrame, VocabularyReport]:
    return reinfer_split(
        "baseline.pt",
        ground_truth,
        split,
        output,
        conf=0.001,
        iou=0.7,
        imgsz=640,
        batch=16,
        device=None,
        quantize=32,
        image_name="name",
        reuse_existing=reuse_existing,
        predictor=predictor,
        class_names=_names,
    )


def test_scores_only_the_requested_split(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    predictor = RecordingPredictor()

    predictions, _ = _reinfer(ground_truth, tmp_path / "out" / "preds.csv", predictor)

    expected = set(ground_truth.loc[ground_truth["split"] == "test", "image_path"])
    assert set(predictor.calls[0][1]) == expected
    assert list(predictions.columns) == PREDICTION_COLUMNS
    assert set(predictions["image_name"]) == {"a.jpg", "b.jpg"}


def test_forwards_the_inference_settings(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    predictor = RecordingPredictor()

    _reinfer(ground_truth, tmp_path / "preds.csv", predictor)

    assert predictor.calls[0][2] == {
        "conf": 0.001,
        "iou": 0.7,
        "imgsz": 640,
        "batch": 16,
        "device": None,
        # Named rather than left to the inference default, so the precision the cache is
        # keyed on is the precision that was passed.
        "quantize": 32,
        "image_name": "name",
    }


def test_writes_predictions_csv(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    output = tmp_path / "nested" / "preds.csv"

    predictions, _ = _reinfer(ground_truth, output, RecordingPredictor())

    assert output.is_file()
    pd.testing.assert_frame_equal(pd.read_csv(output), predictions)


def test_reuses_an_existing_csv_without_inference(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    output = tmp_path / "preds.csv"
    first, _ = _reinfer(ground_truth, output, RecordingPredictor())

    second, _ = _reinfer(ground_truth, output, _explode)

    pd.testing.assert_frame_equal(first, second)


def test_reused_identifiers_keep_their_text_form(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    """Numeric-looking stems must not come back from the cache as integers."""
    output = tmp_path / "preds.csv"
    numeric = NumericNamePredictor()
    first, _ = _reinfer(ground_truth, output, numeric)

    second, _ = _reinfer(ground_truth, output, _explode)

    pd.testing.assert_frame_equal(first, second)
    assert list(second["image_name"]) == ["000000000009", "000000000025"]


def test_reuse_disabled_reruns_inference(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    output = tmp_path / "preds.csv"
    _reinfer(ground_truth, output, RecordingPredictor())
    predictor = RecordingPredictor()

    _reinfer(ground_truth, output, predictor, reuse_existing=False)

    assert len(predictor.calls) == 1


def test_cache_miss_runs_inference(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    predictor = RecordingPredictor()

    _reinfer(ground_truth, tmp_path / "absent.csv", predictor)

    assert len(predictor.calls) == 1


def test_logs_which_branch_was_taken(
    ground_truth: pd.DataFrame, tmp_path: Path, info_logs: list[str]
) -> None:
    """A silent reuse of a stale cache would be indistinguishable from a fresh run."""
    output = tmp_path / "preds.csv"
    _reinfer(ground_truth, output, RecordingPredictor())
    assert any("Re-inferred" in message and str(output) in message for message in info_logs)

    info_logs.clear()
    _reinfer(ground_truth, output, _explode)

    assert any("Reusing" in message and str(output) in message for message in info_logs)


def test_empty_split_raises(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="val"):
        _reinfer(ground_truth, tmp_path / "preds.csv", _explode, split="val")


def test_missing_image_path_column_raises(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    without_paths = ground_truth.drop(columns=["image_path"])

    with pytest.raises(ValueError, match="image_path"):
        _reinfer(without_paths, tmp_path / "preds.csv", _explode)


def test_missing_image_file_raises(ground_truth: pd.DataFrame, tmp_path: Path) -> None:
    Path(str(ground_truth.loc[0, "image_path"])).unlink()

    with pytest.raises(ValueError, match="do not exist on disk"):
        _reinfer(ground_truth, tmp_path / "preds.csv", _explode)


def test_missing_image_is_checked_even_when_the_cache_is_warm(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    output = tmp_path / "preds.csv"
    _reinfer(ground_truth, output, RecordingPredictor())
    Path(str(ground_truth.loc[0, "image_path"])).unlink()

    with pytest.raises(ValueError, match="do not exist on disk"):
        _reinfer(ground_truth, output, _explode)


def test_vocabulary_report_compares_checkpoint_against_the_split(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    with_unknown = pd.concat(
        [
            ground_truth,
            ground_truth.iloc[[0]].assign(instance_label="forklift"),
        ],
        ignore_index=True,
    )

    _, vocabulary = _reinfer(with_unknown, tmp_path / "preds.csv", RecordingPredictor())

    assert vocabulary.model_classes == ["person", "dog", "umbrella"]
    assert vocabulary.unknown_to_model == ["forklift"]
    assert vocabulary.unknown_to_ground_truth == []


def test_vocabulary_report_ignores_classes_from_other_splits(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    """'forklift' lives only in train, so it is not part of the test split's family."""
    _, vocabulary = _reinfer(ground_truth, tmp_path / "preds.csv", RecordingPredictor())

    assert vocabulary.unknown_to_model == []
    assert vocabulary.unknown_to_ground_truth == []


def test_vocabulary_report_lists_classes_the_split_never_shows(
    ground_truth: pd.DataFrame, tmp_path: Path
) -> None:
    without_dogs = ground_truth[ground_truth["instance_label"] != "dog"]

    _, vocabulary = _reinfer(without_dogs, tmp_path / "preds.csv", RecordingPredictor())

    assert vocabulary.unknown_to_ground_truth == ["dog"]
