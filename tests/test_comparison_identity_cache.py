"""Comparison cache reuse must not rebind altered predictions to a model."""

import json
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.adapters.clearml.results import prediction_model_identity
from clearml_yolo.adapters.storage.identity import checkpoint_sha256
from clearml_yolo.adapters.yolo.reinfer import reinfer_split
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.compare import _scored
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.identity import ModelIdentity
from test_comparison_assemble import _settled
from test_comparison_reinfer import RecordingPredictor
from workflow_dependencies import patch_workflow
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@pytest.mark.parametrize("change", ["csv", "identity", "checkpoint", "regenerate", "legacy"])
def test_comparison_cache_preserves_verified_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"model")
    identity = ModelIdentity(
        model_name="source", training_task_id="a" * 32, checkpoint_sha256=checkpoint_sha256(weights)
    )
    truth = pd.DataFrame(
        [
            {
                "image_name": image.name,
                "image_path": str(image),
                "instance_label": "person",
                "split": "test",
                "bbox_x_tl": 1.0,
                "bbox_y_tl": 2.0,
                "bbox_x_br": 3.0,
                "bbox_y_br": 4.0,
            }
        ]
    )
    predictor = RecordingPredictor()
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.compare.reinfer_split",
        partial(reinfer_split, predictor=predictor, class_names=lambda _: {0: "person"}),
    )
    observations: list[list[float]] = []

    def observe(_truth: Any, raw: pd.DataFrame, _prepared: Any, **kwargs: Any) -> Any:
        observations.append(raw["confidence"].tolist())
        return SimpleNamespace()

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.compare.evaluate_split",
        observe,
    )
    output = tmp_path / "predictions.csv"

    def score(*, reuse: bool = True) -> None:
        _scored(
            weights,
            truth,
            "test",
            output,
            tmp_path,
            "candidate",
            _settled().model_copy(update={"reuse_existing": reuse}),
            {"person": 0.0},
            ["person"],
            evaluation=EvaluationConfig(),
            model_identity=identity,
            deps=workflow_dependencies,
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


def test_comparison_resolves_execution_and_fingerprint_without_rewriting_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from clearml_yolo.application.use_cases.compare import (
        _read_comparison_truth,
        _split_fingerprint,
    )

    source = tmp_path / "source"
    source.mkdir()
    image = source / "image.jpg"
    image.write_bytes(b"source image")
    truth_path = source / "truth.csv"
    pd.DataFrame([{
        "image_name": "image.jpg", "image_path": "image.jpg", "instance_label": "person",
        "bbox_x_tl": 1., "bbox_y_tl": 2., "bbox_x_br": 3., "bbox_y_br": 4., "split": "test",
    }]).to_csv(truth_path, index=False)
    working = tmp_path / "hydra-output"
    working.mkdir()
    (working / "image.jpg").write_bytes(b"wrong image")
    monkeypatch.chdir(working)
    loaded = _read_comparison_truth(truth_path, "name", deps=workflow_dependencies)
    assert loaded.source.image_path.tolist() == ["image.jpg"]
    assert loaded.execution.image_path.tolist() == [str(image)]
    fingerprint = _split_fingerprint(loaded.execution, "test", deps=workflow_dependencies)
    monkeypatch.chdir(source)
    assert _split_fingerprint(loaded.execution, "test", deps=workflow_dependencies) == fingerprint
    monkeypatch.chdir(working)
    predictor = RecordingPredictor()
    monkeypatch.setattr(
        workflow_dependencies.model, "reinfer_split",
        partial(reinfer_split, predictor=predictor, class_names=lambda _: {0: "person"}),
    )
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"model")
    observed: list[pd.DataFrame] = []

    def observe(_truth: Any, _raw: Any, _prepared: Any, **kwargs: Any) -> Any:
        observed.append(kwargs["source_ground_truth"])
        return SimpleNamespace()

    patch_workflow(
        monkeypatch, workflow_dependencies,
        "clearml_yolo.application.use_cases.compare.evaluate_split", observe,
    )
    _scored(
        weights, loaded.source, "test", tmp_path / "predictions.csv", tmp_path,
        "candidate", _settled(), {"person": 0.0}, ["person"],
        evaluation=EvaluationConfig(), execution_truth=loaded.execution,
        deps=workflow_dependencies,
    )
    assert predictor.calls[0][1] == [str(image)]
    assert observed[0].image_path.tolist() == ["image.jpg"]
    assert observed[0].source_row_id.tolist() == ["gt:0"]
