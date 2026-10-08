"""Application orchestration uses only explicitly supplied capabilities."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pandas as pd
import pytest

from clearml_yolo.application.contracts import ClearMLConfig, MetricsResult, PredictResult
from clearml_yolo.application.ports import DatasetStore, TrackingSession, WorkflowDependencies
from clearml_yolo.application.use_cases import val
from clearml_yolo.application.use_cases.ground_truth import ground_truth
from clearml_yolo.application.use_cases.pipeline import _as_dict
from clearml_yolo.core.evaluation.models import EvaluationConfig
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


def test_use_case_requires_explicit_dependencies() -> None:
    with pytest.raises(TypeError, match="deps"):
        ground_truth("data.yaml", "truth.csv", ClearMLConfig())  # type: ignore[call-arg]


def test_conversion_uses_supplied_dataset_and_tracking_ports(
    tmp_path: Path, workflow_dependencies: WorkflowDependencies
) -> None:
    task = SimpleNamespace(id="injected-task")
    resolved = tmp_path / "resolved.yaml"
    destination = tmp_path / "truth.csv"
    tracking = Mock(spec=TrackingSession)
    tracking.init_task.return_value = task
    tracking.connect_config_file.return_value = resolved
    dataset = Mock(spec=DatasetStore)
    dataset.build_ground_truth.return_value = destination
    dependencies = replace(
        workflow_dependencies,
        dataset=cast(DatasetStore, dataset),
        tracking=cast(TrackingSession, tracking),
    )

    result = ground_truth(
        "original.yaml",
        "requested.csv",
        ClearMLConfig(),
        test_fraction=0.2,
        seed=17,
        deps=dependencies,
    )

    assert result == destination
    tracking.init_task.assert_called_once_with(ClearMLConfig(), stage="ground_truth")
    tracking.connect_config_file.assert_called_once_with(task, "dataset", Path("original.yaml"))
    dataset.build_ground_truth.assert_called_once_with(
        str(resolved), "requested.csv", test_fraction=0.2, seed=17
    )
    tracking.register_ground_truth.assert_called_once_with(task, destination, output_dir=tmp_path)
    assert not destination.exists()


def test_nested_validation_forwards_the_same_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    task = SimpleNamespace(id="validation-owner")
    monkeypatch.setattr(workflow_dependencies.tracking, "init_task", lambda *a, **k: task)
    predicted = Mock(spec=PredictResult)
    predicted.predictions = tmp_path / "actual.csv"
    metrics = MetricsResult(output_dir=tmp_path / "metrics")
    prediction = Mock(return_value=predicted)
    evaluation = Mock(return_value=metrics)
    monkeypatch.setattr(val, "predict", prediction)
    monkeypatch.setattr(val, "compute_metrics", evaluation)

    result = val.validate(
        "weights.pt",
        "ground_truth.csv",
        tmp_path,
        ClearMLConfig(),
        {},
        EvaluationConfig(),
        splits=["test"],
        deps=workflow_dependencies,
    )

    assert result is metrics
    assert prediction.call_args.kwargs["deps"] is workflow_dependencies
    assert evaluation.call_args.kwargs["deps"] is workflow_dependencies
    assert prediction.call_args.kwargs["splits"] == ["val", "test"]
    assert evaluation.call_args.args[0] == predicted.predictions


def test_stage_normalization_accepts_only_project_request_values() -> None:
    from dataclasses import make_dataclass

    request = make_dataclass("Stage", [("evaluation", object), ("defaults", object)])
    evaluation = EvaluationConfig()
    assert _as_dict(request(evaluation, [])) == {"evaluation": evaluation}
    assert _as_dict({"evaluation": evaluation}) == {"evaluation": evaluation}
    with pytest.raises(TypeError, match="normalized mappings or dataclass"):
        _as_dict(pd.DataFrame())
