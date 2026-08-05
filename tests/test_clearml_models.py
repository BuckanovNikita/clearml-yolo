"""Reading a previous run's checkpoint and thresholds back out of ClearML."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.clearml_models import (
    fetch_best_confidences,
    latest_completed_task_id,
    looks_like_task_id,
    resolve_task_weights,
    resolve_weights,
)

TASK_ID = "a" * 32


class FakeModel:
    def __init__(self, local_copy: str) -> None:
        self._local_copy = local_copy

    def get_local_copy(self) -> str:
        return self._local_copy


class FakeArtifact:
    def __init__(self, local_copy: str = "", payload: Any = None) -> None:
        self._local_copy = local_copy
        self._payload = payload

    def get_local_copy(self) -> str:
        return self._local_copy

    def get(self) -> Any:
        return self._payload


class FakeTask:
    def __init__(
        self,
        models: dict[str, list[FakeModel]] | None = None,
        artifacts: dict[str, FakeArtifact] | None = None,
    ) -> None:
        self.id = TASK_ID
        self.name = "previous-run"
        self._models = models or {}
        self.artifacts = artifacts or {}

    def get_models(self) -> dict[str, list[FakeModel]]:
        return self._models


@pytest.fixture
def patch_clearml(monkeypatch: pytest.MonkeyPatch) -> Any:
    def _patch(task: FakeTask | None) -> None:
        module = types.ModuleType("clearml")
        module.Task = types.SimpleNamespace(  # type: ignore[attr-defined]
            get_task=lambda task_id: task
        )
        monkeypatch.setitem(sys.modules, "clearml", module)

    return _patch


def test_the_baseline_lookup_asks_clearml_for_the_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default baseline is the promoted model, not merely the last run to finish."""
    asked: dict[str, Any] = {}
    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(  # type: ignore[attr-defined]
        get_tasks=lambda **kwargs: asked.update(kwargs) or [FakeTask()]
    )
    monkeypatch.setitem(sys.modules, "clearml", module)

    assert latest_completed_task_id("detection", tags=["prod"]) == TASK_ID
    assert asked["tags"] == ["prod"]
    assert asked["task_filter"]["status"] == ["completed", "published"]


def test_no_promoted_model_is_reported_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(get_tasks=lambda **_: [])  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)

    assert latest_completed_task_id("detection", tags=["prod"]) is None


def test_task_ids_are_told_apart_from_checkpoint_names() -> None:
    assert looks_like_task_id(TASK_ID)
    assert not looks_like_task_id("yolo11n.pt")
    assert not looks_like_task_id("a" * 31)
    assert not looks_like_task_id("z" * 32)


def test_weights_prefers_the_last_registered_output_model(
    patch_clearml: Any, tmp_path: Path
) -> None:
    """Ultralytics registers a checkpoint repeatedly; the last one survived training."""
    last = tmp_path / "best.pt"
    last.write_bytes(b"")
    patch_clearml(
        FakeTask(models={"output": [FakeModel(str(tmp_path / "epoch1.pt")), FakeModel(str(last))]})
    )

    assert resolve_task_weights(TASK_ID) == last


def test_weights_fall_back_to_an_uploaded_checkpoint_artifact(
    patch_clearml: Any, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "manual.pt"
    checkpoint.write_bytes(b"")
    patch_clearml(
        FakeTask(
            artifacts={
                "predictions": FakeArtifact(str(tmp_path / "predictions.csv")),
                "model": FakeArtifact(str(checkpoint)),
            }
        )
    )

    assert resolve_task_weights(TASK_ID) == checkpoint


def test_a_task_without_a_checkpoint_says_so(patch_clearml: Any) -> None:
    patch_clearml(FakeTask())

    with pytest.raises(ValueError, match="no output model"):
        resolve_task_weights(TASK_ID)


def test_local_checkpoints_never_reach_clearml(tmp_path: Path) -> None:
    """A path that exists is used as-is, so predict works with no ClearML at all."""
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")

    assert resolve_weights(checkpoint) == checkpoint


def test_bare_model_names_are_left_for_ultralytics_to_download() -> None:
    assert resolve_weights("yolo11n.pt") == Path("yolo11n.pt")


def test_thresholds_come_back_as_plain_floats(patch_clearml: Any) -> None:
    frame = pd.DataFrame({"confidence": [0.31, 0.47]}, index=["car", "van"])
    patch_clearml(FakeTask(artifacts={"best_confidences_test": FakeArtifact(payload=frame)}))

    assert fetch_best_confidences(TASK_ID, "test") == pytest.approx({"car": 0.31, "van": 0.47})


def test_thresholds_survive_a_json_encoded_artifact(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(artifacts={"best_confidences_val": FakeArtifact(payload='{"car": 0.25}')})
    )

    assert fetch_best_confidences(TASK_ID, "val") == pytest.approx({"car": 0.25})


def test_a_missing_threshold_artifact_names_the_split(patch_clearml: Any) -> None:
    patch_clearml(FakeTask())

    with pytest.raises(ValueError, match="best_confidences_test"):
        fetch_best_confidences(TASK_ID, "test")
