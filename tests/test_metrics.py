"""Validation-only calibration and frozen split evaluation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from clearml_yolo.tasks.metrics import EvaluationConfig, _prepare, compute_metrics

GT_COLUMNS = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]
PRED_COLUMNS = [
    "image_name",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "confidence",
]


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    ground_truth = pd.DataFrame(
        [
            ("val.jpg", "/images/val.jpg", "cat", 0, 0, 10, 10, "val"),
            ("test.jpg", "/images/test.jpg", "cat", 0, 0, 10, 10, "test"),
            ("empty.jpg", "/images/empty.jpg", None, None, None, None, None, "test"),
        ],
        columns=GT_COLUMNS,
    )
    predictions = pd.DataFrame(
        [
            ("val.jpg", "cat", 0, 0, 10, 10, 0.8),
            ("val.jpg", "cat", 20, 20, 30, 30, 0.3),
            ("test.jpg", "cat", 0, 0, 10, 10, 0.6),
            ("empty.jpg", "cat", 20, 20, 30, 30, 0.7),
        ],
        columns=PRED_COLUMNS,
    )
    predictions_path = tmp_path / "predictions.csv"
    ground_truth_path = tmp_path / "ground_truth.csv"
    predictions.to_csv(predictions_path, index=False)
    ground_truth.to_csv(ground_truth_path, index=False)
    return predictions_path, ground_truth_path


def test_candidate_threshold_is_calibrated_on_val_and_reused_for_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)

    result = compute_metrics(
        predictions,
        ground_truth,
        tmp_path / "metrics",
        clearml=object(),  # type: ignore[arg-type]
        evaluation=EvaluationConfig(),
        splits=["val", "test"],
        calibration_split="val",
    )

    assert result.best_confidences["val"] == {"cat": 0.8}
    assert result.best_confidences["test"] == {"cat": 0.8}
    test = pd.read_excel(result.dashboards["test"], index_col=0)
    assert test.loc["cat", "confidence"] == pytest.approx(0.8)
    assert test.loc["cat", "tp"] == 0
    assert test.loc["cat", "fn"] == 1
    assert test.loc["cat", "fp"] == 0
    for split in ("val", "test"):
        for metric in ("recall", "precision", "perebrak", "nedobrak"):
            assert (
                tmp_path / "metrics" / f"{metric}_confidence_intervals_{split}.png"
            ).is_file()
        assert (tmp_path / "metrics" / f"matrix_{split}.xlsx").is_file()


def test_test_only_evaluation_still_requires_validation_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    frame = pd.read_csv(ground_truth)
    frame = frame[frame["split"] == "test"]
    frame.to_csv(ground_truth, index=False)
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="calibration split 'val'"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=object(),  # type: ignore[arg-type]
            evaluation=EvaluationConfig(),
            splits=["test"],
            calibration_split="val",
        )


def test_calibration_split_must_be_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="exactly 'val'"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=object(),  # type: ignore[arg-type]
            evaluation=EvaluationConfig(),
            splits=["test"],
            calibration_split="test",
        )


def test_one_image_cannot_belong_to_validation_and_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    frame = pd.read_csv(ground_truth)
    frame.loc[frame["split"] == "test", "image_name"] = "val.jpg"
    frame.to_csv(ground_truth, index=False)
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match=r"both val and test.*val\.jpg"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=object(),  # type: ignore[arg-type]
            evaluation=EvaluationConfig(),
            splits=["test"],
        )


def test_prediction_only_classes_are_preserved_for_false_positive_accounting() -> None:
    ground_truth = pd.DataFrame(
        [("val.jpg", "/images/val.jpg", "cat", 0, 0, 10, 10, "val")],
        columns=GT_COLUMNS,
    )
    predictions = pd.DataFrame(
        [
            ("val.jpg", "cat", 0, 0, 10, 10, 0.8),
            ("val.jpg", "bird", 20, 20, 30, 30, 0.7),
        ],
        columns=PRED_COLUMNS,
    )

    _, raw, prepared, classes = _prepare(predictions, ground_truth, EvaluationConfig())

    assert classes == ["bird", "cat"]
    assert list(raw["instance_label"]) == ["cat", "bird"]
    assert list(prepared["instance_label"]) == ["cat", "bird"]


def test_numeric_image_identifiers_remain_text_when_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    prediction_frame = pd.read_csv(predictions).assign(
        image_name=["000000000009", "000000000009", "000000000025", "000000000031"]
    )
    truth_frame = pd.read_csv(ground_truth).assign(
        image_name=["000000000009", "000000000025", "000000000031"]
    )
    prediction_frame.to_csv(predictions, index=False)
    truth_frame.to_csv(ground_truth, index=False)
    seen: dict[str, pd.DataFrame] = {}

    def capture(
        prediction_data: pd.DataFrame,
        truth_data: pd.DataFrame,
        _config: EvaluationConfig,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
        seen["predictions"] = prediction_data
        seen["ground_truth"] = truth_data
        raise RuntimeError("captured")

    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("clearml_yolo.tasks.metrics._prepare", capture)

    with pytest.raises(RuntimeError, match="captured"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=object(),  # type: ignore[arg-type]
            evaluation=EvaluationConfig(),
            splits=["test"],
        )

    assert seen["predictions"]["image_name"].iloc[0] == "000000000009"
    assert seen["ground_truth"]["image_name"].iloc[0] == "000000000009"
