"""The predict stage records the scale it inferred at, not only the boxes it found."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo import artifact_names
from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks import predict as predict_module
from clearml_yolo.tasks.predict import predict


@pytest.fixture
def checkpoint_recording(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stand in for the checkpoint reader, which would otherwise need a real .pt file."""

    def _record(train_args: dict[str, Any]) -> None:
        module = types.ModuleType("ultralytics.nn.tasks")
        module.torch_safe_load = lambda path: ({"train_args": train_args}, path)  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "ultralytics.nn.tasks", module)

    return _record


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> dict[str, pd.DataFrame]:
    """Everything the stage would have published to ClearML, keyed by section/series."""
    tables: dict[str, pd.DataFrame] = {}

    def report_table(_: object, title: str, series: str, frame: pd.DataFrame) -> None:
        tables[f"{title}/{series}"] = frame

    monkeypatch.setattr(predict_module, "report_table", report_table)
    monkeypatch.setattr(predict_module, "resolve_weights", lambda weights: weights)
    monkeypatch.setattr(
        predict_module, "predict_on_images", lambda *_, **__: pd.DataFrame({"image_name": []})
    )
    return tables


def _ground_truth(tmp_path: Path) -> Path:
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_path,split\na.png,test\n")
    return truth


def _predict(tmp_path: Path, imgsz: int | None) -> Any:
    return predict(
        weights="best.pt",
        ground_truth=_ground_truth(tmp_path),
        output=tmp_path / "predictions.csv",
        clearml=ClearMLConfig(enabled=False),
        ultralytics={"imgsz": imgsz, "device": "cpu", "batch": 1},
    )


def test_the_scale_inference_ran_at_reaches_the_run_record(
    tmp_path: Path, checkpoint_recording: Any, published: dict[str, pd.DataFrame]
) -> None:
    """ClearML captures the warning in the console log, where an hour of a run buries it.
    The table is the same fact somewhere a reviewer can find it later."""
    checkpoint_recording({"imgsz": 1280})

    _predict(tmp_path, 640)

    section = f"{artifact_names.PREDICT_SECTION}/{artifact_names.RESOLUTION_SERIES}"
    rows = published[section]
    assert dict(zip(rows["parameter"], rows["value"], strict=True)) == {
        "trained at imgsz": "1280",
        "scored at imgsz": "640",
        "same resolution?": "NO — scored at a scale this model was never shown",
    }


def test_the_resolution_travels_with_the_predictions(
    tmp_path: Path, checkpoint_recording: Any, published: dict[str, pd.DataFrame]
) -> None:
    """The report stage publishes numbers measured at this scale, and reopening the
    checkpoint to ask a second time is how the two would come to disagree."""
    checkpoint_recording({"imgsz": 1280})

    result = _predict(tmp_path, None)

    assert result.predictions == tmp_path / "predictions.csv"
    assert result.resolution.scored_at == 1280
    assert not result.resolution.was_trained_elsewhere
