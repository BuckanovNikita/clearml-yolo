"""Training success survives publication faults without claiming delivered artifacts."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.clearml.console import ConsolePublicationError
from clearml_yolo.adapters.storage.file_io import atomic_write_text
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.pipeline_outcome import PipelineOutcome, StageOutcome
from test_clearml_session import FakeTask


def _state(tmp_path: Path) -> session._InvocationState:
    return session._InvocationState(
        task=FakeTask(),
        stages=["pipeline"],
        current_stage="pipeline",
        pipeline_outcome=PipelineOutcome(training_succeeded=True),
        outcome_path=tmp_path / "pipeline_outcome.json",
    )


def test_missing_upload_preserves_training_and_records_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(tmp_path)
    state.artifacts.append(
        session._ArtifactRecord(
            name="report",
            required=True,
            uploaded=False,
            stage="report",
            local_path=None,
        )
    )
    monkeypatch.setattr(session, "_release_failure_monitor", lambda _state: None)
    monkeypatch.setattr(session, "_close_for_failure", lambda _state, _error: state.task)
    session._finalize_preserving_training(state)
    record = json.loads(state.outcome_path.read_text())  # type: ignore[union-attr]
    assert record["status"] == "completed_with_warnings"
    assert "report" in record["stages"]["publication"]["reason"]
    assert not state.artifacts[0].uploaded
    assert state.task.uploads[-1]["artifact_object"]["status"] == "completed_with_warnings"
    assert not state.task.failed
    assert state.task.completed[0]["status_message"].startswith("completed_with_warnings:")


def test_standalone_finalization_failure_remains_strict() -> None:
    state = session._InvocationState(task=FakeTask(), stages=["report"], current_stage="report")
    state.task.flush_result = False
    with pytest.raises(session.ArtifactUploadError):
        session._finalize_preserving_training(state)


def test_interruption_remains_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(tmp_path)

    def interrupt(_state: session._InvocationState) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(session, "_finalize", interrupt)
    with pytest.raises(KeyboardInterrupt):
        session._finalize_preserving_training(state)


def test_unreachable_status_retains_local_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(tmp_path)
    state.task.flush_result = False

    def unavailable(_state: session._InvocationState) -> None:
        raise ConnectionError("network unavailable")

    monkeypatch.setattr(session, "_release_failure_monitor", unavailable)
    session._finalize_preserving_training(state)
    assert state.outcome_path is not None
    recorded = json.loads(state.outcome_path.read_text())
    assert recorded["status"] == "completed_with_warnings"
    assert "Completion status update failed" in recorded["stages"]["publication"]["reason"]


def test_success_marker_requires_checkpoint_and_pipeline(tmp_path: Path) -> None:
    task = FakeTask()
    state = session._InvocationState(task=task, stages=["pipeline"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        weights = tmp_path / "best.pt"
        with pytest.raises(ValueError, match="nonempty"):
            session.preserve_training_success(task, weights, tmp_path / "pipeline_outcome.json")
        weights.write_bytes(b"weights")
        session.preserve_training_success(task, weights, tmp_path / "pipeline_outcome.json")
        assert state.pipeline_outcome is not None
        assert state.pipeline_outcome.training_succeeded
        session.register_training_counts(task, weights, {"a": 12})
        digest = next(iter(state.checkpoint_training_counts))
        assert session.training_counts(ModelIdentity(model_name="a", checkpoint_sha256=digest)) == {
            "a": 12,
        }
        other = ModelIdentity(model_name="a", checkpoint_sha256="other")
        assert session.training_counts(other) is None
    finally:
        session._ACTIVE_INVOCATION.reset(token)


def test_pipeline_record_preserves_earlier_model_publication_failure(tmp_path: Path) -> None:
    state = _state(tmp_path)
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        assert session.record_training_publication_failure(state.task, ConnectionError("offline"))
        updated = PipelineOutcome(training_succeeded=True)
        updated.stages["metrics"] = StageOutcome(status="succeeded")
        session.record_pipeline_outcome(state.task, updated)
        assert updated.status == "completed_with_warnings"
        assert updated.stages["publication"].status == "failed"
    finally:
        session._ACTIVE_INVOCATION.reset(token)


def test_atomic_snapshot_keeps_previous_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "outcome.json"
    destination.write_text("old")

    def fail_replace(self: Path, target: Any) -> Path:
        raise OSError("disk unavailable")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="unavailable"):
        atomic_write_text(destination, "new")
    assert destination.read_text() == "old"
    assert list(tmp_path.iterdir()) == [destination]


def test_late_console_failure_preserves_training(tmp_path: Path) -> None:
    state = _state(tmp_path)

    class Console:
        def finish(self) -> None:
            raise ConsolePublicationError("delivery failed")

    state.console_publisher = Console()  # type: ignore[assignment]
    session._finish_console(state, None)
    assert state.pipeline_outcome is not None
    assert state.pipeline_outcome.status == "completed_with_warnings"
    assert not state.task.failed


def test_publication_warning_does_not_soften_interrupted_console(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(tmp_path)
    monkeypatch.setitem(
        sys.modules,
        "clearml",
        SimpleNamespace(Task=SimpleNamespace(get_task=lambda **_kwargs: state.task)),
    )

    class Console:
        def finish(self) -> None:
            raise KeyboardInterrupt

    state.console_publisher = Console()  # type: ignore[assignment]
    with pytest.raises(KeyboardInterrupt):
        session._finish_console(state, None)
    assert state.outcome_path is not None
    assert json.loads(state.outcome_path.read_text())["status"] == "failed"
