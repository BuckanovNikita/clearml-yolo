"""Complete results become visible before the invocation verification barrier."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.adapters.clearml import results, session
from clearml_yolo.application.ports import ResultProducer
from clearml_yolo.application.use_cases.compare import NoBaselineModelError
from test_clearml_results import _inputs
from test_clearml_session import FakeTask
from test_clearml_session import fake_clearml as owner_fixture

owner = owner_fixture


def _names(task: FakeTask) -> list[str]:
    return [item["name"] for item in task.uploads]


def test_truth_upload_is_immediate_and_identical_registration_is_a_noop(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, _ = _inputs(tmp_path)
    with session.invocation(session.ClearMLConfig(), "train"):
        results.register_ground_truth(task, truth, output_dir=tmp_path)
        assert _names(task) == ["gt_csv"]
        canonical = Path(task.uploads[0]["artifact_object"])
        modified = canonical.stat().st_mtime_ns
        results.register_ground_truth(task, truth, output_dir=tmp_path)
        assert canonical.stat().st_mtime_ns == modified
        assert _names(task) == ["gt_csv"]
        assert not task.completed
    assert task.completed


def test_last_declared_producer_publishes_the_enriched_aggregate_once(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        results.declare_result_producers(
            task, ["predict", "metrics", "compare"], output_dir=tmp_path
        )
        results.declare_result_producers(task, ["predict"], output_dir=tmp_path)
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        results.complete_result_producer(task, "predict")
        assert _names(task) == ["gt_csv"]
        bundle = results._bundle(task, tmp_path)
        context, shard = next(iter(bundle.contexts.values()))
        rows = pd.read_csv(shard).assign(evaluation_status="evaluated")
        bundle.put(context, rows)
        results.complete_result_producer(task, "metrics")
        assert _names(task) == ["gt_csv"]
        # Automatic baseline absence has no new rows but still completes its contribution.
        results.complete_result_producer(task, "compare")
        assert _names(task) == ["gt_csv", "predicts_csv"]
        exported = pd.read_csv(task.uploads[-1]["artifact_object"])
        assert "evaluated" in set(exported.evaluation_status)
        assert not task.completed
    assert _names(task) == ["gt_csv", "predicts_csv"]


def test_incomplete_contributors_fail_the_barrier_without_uploading_partial_rows(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with pytest.raises(RuntimeError, match="Incomplete result producers"), session.invocation(  # noqa: PT012 - verification occurs on context exit
        session.ClearMLConfig(), "pipeline"
    ):
        results.declare_result_producers(task, ["predict", "metrics"], output_dir=tmp_path)
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        results.complete_result_producer(task, "predict")
    assert _names(task) == ["gt_csv"]
    assert task.failed
    assert not task.completed
    assert list((tmp_path / "result_publication/contexts").glob("*.csv"))


@pytest.mark.parametrize("error", [RuntimeError("later report failure"), KeyboardInterrupt()])
@pytest.mark.parametrize("complete", [False, True])
def test_later_failure_preserves_only_already_complete_publications(
    owner: tuple[type[Any], FakeTask], tmp_path: Path, error: BaseException, complete: bool
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with (  # noqa: PT012 - the invocation must observe the later failure
        pytest.raises(type(error)),
        session.invocation(session.ClearMLConfig(), "pipeline"),
    ):
        results.declare_result_producers(task, ["predict"], output_dir=tmp_path)
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        if complete:
            results.complete_result_producer(task, "predict")
        raise error
    assert _names(task) == ["gt_csv", *(["predicts_csv"] if complete else [])]
    assert task.failed
    assert not task.completed


def test_completed_results_reject_late_rows_duplicate_completion_and_new_producers(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with session.invocation(session.ClearMLConfig(), "predict"):
        results.declare_result_producers(task, ["predict"], output_dir=tmp_path)
        with pytest.raises(ValueError, match="not declared"):
            results.complete_result_producer(task, "metrics")
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        results.complete_result_producer(task, "predict")
        with pytest.raises(ValueError, match="already complete"):
            results.complete_result_producer(task, "predict")
        with pytest.raises(RuntimeError, match="complete"):
            results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        with pytest.raises(ValueError, match="declared"):
            results.declare_result_producers(task, ["metrics"], output_dir=tmp_path)
    assert _names(task) == ["gt_csv", "predicts_csv"]


def test_conflicting_truth_never_replaces_uploaded_canonical_bytes(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, _ = _inputs(tmp_path)
    with session.invocation(session.ClearMLConfig(), "train"):
        results.register_ground_truth(task, truth, output_dir=tmp_path)
        canonical = Path(task.uploads[0]["artifact_object"])
        original = canonical.read_bytes()
        other = tmp_path / "other.csv"
        pd.read_csv(truth).assign(split="train").to_csv(other, index=False)
        with pytest.raises(ValueError, match="conflicting"):
            results.register_ground_truth(task, other, output_dir=tmp_path)
        assert canonical.read_bytes() == original
        assert _names(task) == ["gt_csv"]


@pytest.mark.parametrize("rejected", ["gt_csv", "predicts_csv"])
def test_upload_rejection_fails_at_the_first_complete_artifact(
    owner: tuple[type[Any], FakeTask], tmp_path: Path, rejected: str
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with pytest.raises(session.ArtifactUploadError), session.invocation(  # noqa: PT012 - rejection must cross the owner boundary
        session.ClearMLConfig(), "predict"
    ):
        results.declare_result_producers(task, ["predict"], output_dir=tmp_path)
        task.upload_result = rejected != "gt_csv"
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
        assert rejected == "predicts_csv"
        task.upload_result = False
        results.complete_result_producer(task, "predict")
    assert task.failed
    assert not task.completed


def test_empty_declaration_and_skipped_producer_do_not_invent_prediction_rows(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        results.declare_result_producers(task, [], output_dir=tmp_path)
    assert task.uploads == []
    with session.invocation(session.ClearMLConfig(), "compare"):
        results.declare_result_producers(task, ["compare"], output_dir=tmp_path)
        results.complete_result_producer(task, "compare")
    assert task.uploads == []


def test_undeclared_results_fail_before_they_can_modify_the_bundle(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with (
        session.invocation(session.ClearMLConfig(), "predict"),
        pytest.raises(RuntimeError, match="Declare result producers"),
    ):
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
    assert task.uploads == []


@pytest.mark.parametrize("skip_predict", [False, True])
@pytest.mark.parametrize("skip_metrics", [False, True])
@pytest.mark.parametrize("skip_compare", [False, True])
def test_pipeline_declares_enabled_producers_and_finishes_before_reports(
    owner: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    skip_predict: bool,
    skip_metrics: bool,
    skip_compare: bool,
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.application.use_cases import pipeline
    from clearml_yolo.core.evaluation.models import EvaluationConfig
    from clearml_yolo.core.publication import FiftyOneConfig
    from clearml_yolo.entrypoints.composition import build_dependencies
    from native_config_helpers import prediction_config

    _, task = owner
    deps = build_dependencies()
    truth, predictions = _inputs(tmp_path)
    directory = tmp_path / "run"
    (directory / "metrics").mkdir(parents=True)
    (directory / "metrics/frozen_thresholds.json").write_text(json.dumps({"01": 0.5}))
    stages: tuple[tuple[ResultProducer, bool], ...] = (
        ("predict", skip_predict), ("metrics", skip_metrics), ("compare", skip_compare)
    )
    expected = {name for name, skipped in stages if not skipped}
    visited: list[str] = []

    def contribute(name: Any) -> SimpleNamespace:
        bundle = results._bundle(task)
        assert bundle.producers == frozenset(expected)
        results.declare_result_producers(task, [name], output_dir=directory)
        results.register_predictions(task, truth, predictions, output_dir=directory)
        results.complete_result_producer(task, name)
        visited.append(name)
        if set(visited) == expected:
            assert "predicts_csv" in _names(task)
        else:
            assert "predicts_csv" not in _names(task)
        return SimpleNamespace(
            predictions=predictions, best_confidences={"val": {"01": 0.5}}, evaluations={}
        )

    def skipped_comparison(*_args: Any, **_kwargs: Any) -> None:
        assert results._bundle(task).producers == frozenset(expected)
        visited.append("compare")
        raise NoBaselineModelError("No automatic baseline")

    def report_after_results(*_args: Any, **_kwargs: Any) -> None:
        assert set(visited) == expected
        assert ("predicts_csv" in _names(task)) == bool(expected - {"compare"})
        assert not task.completed

    monkeypatch.setattr(deps.storage, "point_latest_at", lambda *_args: None)
    monkeypatch.setattr(pipeline, "run_prediction", lambda *_a, **_kw: contribute("predict"))
    monkeypatch.setattr(pipeline, "compute_metrics", lambda *_a, **_kw: contribute("metrics"))
    monkeypatch.setattr(pipeline, "run_comparison", skipped_comparison)
    monkeypatch.setattr(pipeline, "run_report", report_after_results)
    monkeypatch.setattr(pipeline, "_publish_pipeline", report_after_results)
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        pipeline.run_pipeline(
            ultralytics={}, ultralytics_predict=prediction_config(),
            metrics={"evaluation": EvaluationConfig(), "calibration_split": "val"},
            report={}, compare={}, clearml=session.ClearMLConfig(), ground_truth=str(truth),
            run_dir=directory, weights=tmp_path / "best.pt", skip_train=True,
            skip_predict=skip_predict, skip_metrics=skip_metrics, skip_compare=skip_compare,
            fiftyone=FiftyOneConfig(enabled=False), model_label="fixture", deps=deps,
        )
    assert task.completed
