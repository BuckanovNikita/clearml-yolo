"""Recovery and provenance stay paired when a source task changes."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from clearml_yolo.tasks.compare import ModelRef, _resolve_model


def test_weights_and_provenance_use_one_source_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "selected.pt"
    checkpoint.write_bytes(b"selected weights")
    selected = SimpleNamespace(
        id="selected-model",
        url="https://files.example/selected.pt",
        get_metadata=lambda key: "best" if key == "clearml_yolo_checkpoint_role" else None,
        get_local_copy=lambda: str(checkpoint),
    )
    later = SimpleNamespace(
        id="later-model",
        url="https://files.example/later.pt",
        get_metadata=lambda key: "best" if key == "clearml_yolo_checkpoint_role" else None,
    )
    snapshots = iter([{"output": [selected]}, {"output": [later]}])
    task = SimpleNamespace(
        id="source-task",
        name="source",
        get_models=lambda: next(snapshots),
        get_output_log_web_page=lambda: "https://clearml.example/source-task",
    )
    monkeypatch.setattr("clearml_yolo.clearml_models._task", lambda _task_id: task)

    # Explicit thresholds also prove that recovery never accesses missing artifacts.
    resolved = _resolve_model(
        ModelRef(task_id="source-task", thresholds={"001": 0.1234567890123456}),
        "project",
        exclude_task_id=None,
        automatic_absence_is_skip=False,
    )

    assert resolved.weights == checkpoint
    assert resolved.links["model_id"] == "selected-model"
    assert resolved.links["model_url"] == "https://files.example/selected.pt"
    assert resolved.thresholds == {"001": 0.1234567890123456}
