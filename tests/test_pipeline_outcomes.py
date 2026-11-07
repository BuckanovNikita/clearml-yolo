"""Post-training failures retain weights and disclose unavailable downstream work."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.application.contracts import ClearMLConfig
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases import pipeline
from clearml_yolo.core.pipeline_outcome import PipelineOutcome, StageOutcome
from clearml_yolo.core.publication import FiftyOneConfig
from native_config_helpers import prediction_config, training_settings
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


@pytest.fixture
def pipeline_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> dict[str, Any]:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    checkpoint = tmp_path / "actual.pt"
    checkpoint.write_bytes(b"verified checkpoint fixture")
    monkeypatch.setattr(workflow_dependencies.tracking, "init_task", lambda *_a, **_k: None)
    for method in (
        "declare_result_producers",
        "complete_result_producer",
        "record_run_configuration",
        "preserve_training_success",
        "record_pipeline_outcome",
    ):
        monkeypatch.setattr(workflow_dependencies.tracking, method, lambda *_a, **_k: None)
    monkeypatch.setattr(workflow_dependencies.storage, "point_latest_at", lambda *_a: None)
    monkeypatch.setattr(workflow_dependencies.resources, "training_finished", lambda: None)
    monkeypatch.setattr(
        pipeline,
        "run_training",
        lambda *_a, **_k: SimpleNamespace(weights=checkpoint, cleaned_ground_truth=tmp_path / "truth.csv"),
    )

    def predict(*args: Any, **_kwargs: Any) -> SimpleNamespace:
        path = args[2]
        path.write_text("image_name\ncurrent\n", encoding="utf-8")
        return SimpleNamespace(predictions=path)

    monkeypatch.setattr(pipeline, "run_prediction", predict)
    monkeypatch.setattr(
        pipeline,
        "compute_metrics",
        lambda *_a, **_k: SimpleNamespace(best_confidences={"val": {"cat": 0.5}}, evaluations={}),
    )
    monkeypatch.setattr(pipeline, "_compare_and_report", lambda *_a, **_k: {"comparison": object()})
    monkeypatch.setattr(
        pipeline,
        "run_report",
        lambda *_a, **_k: SimpleNamespace(issues=(), dev_reports={}, business_reports={}),
    )
    return {
        "ultralytics": training_settings(),
        "ultralytics_predict": prediction_config(),
        "metrics": {"evaluation": object(), "calibration_split": "val"},
        "report": {},
        "compare": {},
        "clearml": ClearMLConfig(),
        "ground_truth": str(tmp_path / "truth.csv"),
        "run_dir": tmp_path / "run",
        "fiftyone": FiftyOneConfig(enabled=False),
        "deps": workflow_dependencies,
    }


@pytest.mark.parametrize(
    ("operation", "stage", "skipped"),
    [
        ("run_prediction", "prediction", ["metrics", "comparison", "report"]),
        ("compute_metrics", "metrics", ["comparison", "report"]),
        ("_compare_and_report", "comparison", ["report"]),
        ("run_report", "report", []),
    ],
)
def test_failed_downstream_stage_preserves_training_without_reusing_stale_outputs(
    pipeline_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    stage: str,
    skipped: list[str],
) -> None:
    directory = pipeline_case["run_dir"]
    directory.mkdir()
    (directory / "predictions.csv").write_text("stale", encoding="utf-8")

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("invalid downstream input token=secret-value")

    monkeypatch.setattr(pipeline, operation, fail)
    result = pipeline.run_pipeline(**pipeline_case)
    outcome = json.loads((directory / "pipeline_outcome.json").read_text())
    assert outcome["training_succeeded"] is True
    assert outcome["status"] == "completed_with_warnings"
    assert outcome["stages"][stage]["status"] == "failed"
    assert "secret-value" not in json.dumps(outcome)
    assert result["weights"].read_bytes() == b"verified checkpoint fixture"
    for name in skipped:
        assert outcome["stages"][name]["status"] == "skipped"
    assert "completed_with_warnings" in (directory / "pipeline_outcome.txt").read_text()


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit])
def test_interruption_is_not_converted_to_success(
    pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch, error: type[BaseException]
) -> None:
    def interrupt(*_args: Any, **_kwargs: Any) -> None:
        raise error()

    monkeypatch.setattr(pipeline, "run_prediction", interrupt)
    with pytest.raises(error):
        pipeline.run_pipeline(**pipeline_case)
    outcome = json.loads((pipeline_case["run_dir"] / "pipeline_outcome.json").read_text())
    assert outcome["status"] == "failed"
    assert outcome["fatal_error"] is True
    assert outcome["training_succeeded"] is True
    assert outcome["stages"]["prediction"]["status"] == "failed"
    assert error.__name__ in outcome["stages"]["prediction"]["reason"]
    assert (pipeline_case["run_dir"].parent / "actual.pt").is_file()


def test_skip_training_keeps_failure_exit(pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("prediction failed")

    monkeypatch.setattr(pipeline, "run_prediction", fail)
    with pytest.raises(ValueError, match="prediction failed"):
        pipeline.run_pipeline(**pipeline_case, skip_train=True, weights="existing.pt")


def test_outcome_status_never_claims_failed_stage_succeeded() -> None:
    outcome = PipelineOutcome(stages={"metrics": StageOutcome(status="failed", reason="bad")})
    initial_status = outcome.status
    assert initial_status == "failed"
    outcome.training_succeeded = True
    assert outcome.status == "completed_with_warnings"
    assert outcome.stages["metrics"].status == "failed"


def test_training_failure_is_not_downgraded(pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("native training failed")

    monkeypatch.setattr(pipeline, "run_training", fail)
    with pytest.raises(RuntimeError, match="native training failed"):
        pipeline.run_pipeline(**pipeline_case)


def test_empty_training_checkpoint_is_not_success(pipeline_case: dict[str, Any]) -> None:
    (pipeline_case["run_dir"].parent / "actual.pt").write_bytes(b"")
    with pytest.raises(ValueError, match="usable checkpoint"):
        pipeline.run_pipeline(**pipeline_case)


def test_report_issues_are_visible_in_outcome(pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_report",
        lambda *_a, **_k: SimpleNamespace(
            issues=(object(),), dev_reports={"test": Path("dev.xlsx")}, business_reports={}
        ),
    )
    result = pipeline.run_pipeline(**pipeline_case)
    assert result["outcome"]["status"] == "completed_with_warnings"
    assert result["outcome"]["stages"]["report"]["status"] == "completed_with_warnings"
    assert result["outcome"]["stages"]["report"]["artifacts"] == ["dev.xlsx"]


def test_tracking_failure_still_writes_local_outcome(
    pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("tracking unavailable")

    monkeypatch.setattr(pipeline_case["deps"].tracking, "record_pipeline_outcome", fail)
    result = pipeline.run_pipeline(**pipeline_case)
    assert "reports" in result
    outcome = json.loads((pipeline_case["run_dir"] / "pipeline_outcome.json").read_text())
    assert outcome["status"] == "completed_with_warnings"
    assert outcome["stages"]["outcome_publication"]["reason"] == "tracking unavailable"


def test_resource_transition_failure_prevents_all_downstream_compute(
    pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_transition() -> None:
        raise RuntimeError("durable contraction completed but resource transition failed")

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("Downstream work cannot run without confirmed resource admission")

    monkeypatch.setattr(pipeline_case["deps"].resources, "training_finished", fail_transition)
    for name in (
        "run_prediction",
        "compute_metrics",
        "_compare_and_report",
        "run_report",
        "_publish_pipeline",
    ):
        monkeypatch.setattr(pipeline, name, forbidden)
    result = pipeline.run_pipeline(**pipeline_case)
    outcome = json.loads((pipeline_case["run_dir"] / "pipeline_outcome.json").read_text())
    assert result["weights"].is_file()
    assert outcome["status"] == "completed_with_warnings"
    assert outcome["stages"]["training_resources"]["status"] == "failed"
    assert outcome["stages"]["training_metadata"]["status"] == "succeeded"
    for name in ("prediction", "metrics", "comparison", "report", "visualization"):
        assert outcome["stages"][name]["status"] == "skipped"
        assert "resource transition failed" in outcome["stages"][name]["reason"]


def test_successful_report_records_artifacts(pipeline_case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_report",
        lambda *_a, **_k: SimpleNamespace(
            issues=(),
            dev_reports={"test": Path("dev.xlsx")},
            business_reports={"test": Path("business.xlsx")},
        ),
    )
    result = pipeline.run_pipeline(**pipeline_case)
    stage = result["outcome"]["stages"]["report"]
    assert stage["status"] == "succeeded"
    assert stage["artifacts"] == ["dev.xlsx", "business.xlsx"]
