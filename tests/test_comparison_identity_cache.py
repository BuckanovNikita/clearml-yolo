"""Comparison cache reuse must not rebind altered predictions to a model."""

import json
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.clearml_results import prediction_model_identity
from clearml_yolo.comparison.reinfer import reinfer_split
from clearml_yolo.comparison.scoring import EvaluationConfig
from clearml_yolo.model_identity import ModelIdentity, checkpoint_sha256
from clearml_yolo.tasks.compare import _scored
from test_comparison_assemble import _settled
from test_comparison_reinfer import RecordingPredictor


@pytest.mark.parametrize("change", ["csv", "identity", "checkpoint", "regenerate", "legacy"])
def test_comparison_cache_preserves_verified_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str,
) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"model")
    identity = ModelIdentity(
        model_name="source", training_task_id="a" * 32,
        checkpoint_sha256=checkpoint_sha256(weights),
    )
    truth = pd.DataFrame([{
        "image_name": image.name, "image_path": str(image), "instance_label": "person",
        "split": "test", "bbox_x_tl": 1.0, "bbox_y_tl": 2.0,
        "bbox_x_br": 3.0, "bbox_y_br": 4.0,
    }])
    predictor = RecordingPredictor()
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        partial(reinfer_split, predictor=predictor, class_names=lambda _: {0: "person"}),
    )
    observations: list[list[float]] = []

    def observe(_truth: Any, raw: pd.DataFrame, _prepared: Any, **kwargs: Any) -> Any:
        observations.append(raw["confidence"].tolist())
        return SimpleNamespace()

    monkeypatch.setattr("clearml_yolo.tasks.compare.evaluate_split", observe)
    output = tmp_path / "predictions.csv"

    def score(*, reuse: bool = True) -> None:
        _scored(
            weights, truth, "test", output, tmp_path, "candidate",
            _settled().model_copy(update={"reuse_existing": reuse}), {"person": 0.0},
            ["person"], evaluation=EvaluationConfig(), model_identity=identity,
        )

    score()
    sidecar = output.with_suffix(".csv.provenance.json")
    if change in {"csv", "regenerate"}:
        output.write_text(output.read_text().replace("0.9", "0.1"))
    elif change == "identity":
        payload = json.loads(sidecar.read_text())
        payload["model_identity"]["training_task_id"] = "b" * 32
        sidecar.write_text(json.dumps(payload))
    elif change == "checkpoint":
        weights.write_bytes(b"different model")
    else:
        sidecar.unlink()
    if change in {"csv", "identity", "checkpoint"}:
        original = sidecar.read_bytes()
        with pytest.raises(ValueError, match=r"provenance|identity|checkpoint"):
            score()
        assert sidecar.read_bytes() == original
        assert len(predictor.calls) == 1
        assert observations == [[0.9]]
    else:
        score(reuse=change == "legacy")
        assert len(predictor.calls) == (1 if change == "legacy" else 2)
        assert prediction_model_identity(output) == identity
        assert observations == [[0.9], [0.9]]
