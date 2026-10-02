"""Reading a previous run's checkpoint and thresholds back out of ClearML."""

import sys
import types
from pathlib import Path
from typing import Any, override

import pandas as pd
import pytest

from clearml_yolo.artifact_names import BEST_CONFIDENCES_VAL
from clearml_yolo.clearml_models import (
    fetch_best_confidences,
    latest_completed_task_id,
    looks_like_task_id,
    resolve_task_weights,
    resolve_weights,
)

TASK_ID = "a" * 32


class FakeModel:
    def __init__(self, local_copy: str, *, checkpoint_role: str | None = None) -> None:
        self._local_copy = local_copy
        self._checkpoint_role = checkpoint_role
        self.url = "https://files.example/" + Path(local_copy).name
        self.id = Path(local_copy).stem

    def get_metadata(self, key: str) -> str | None:
        if key == "clearml_yolo_checkpoint_role":
            return self._checkpoint_role
        return None

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


class ExplodingArtifact(FakeArtifact):
    @override
    def get_local_copy(self) -> str:
        raise AssertionError("non-checkpoint artifacts must not be downloaded")


class FakeTask:
    def __init__(
        self,
        models: dict[str, list[FakeModel]] | None = None,
        artifacts: dict[str, FakeArtifact] | None = None,
        task_id: str = TASK_ID,
    ) -> None:
        self.id = task_id
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


def _recording_clearml_module(asked: dict[str, Any]) -> types.ModuleType:
    """A stand-in ``clearml`` whose ``Task.get_tasks`` records the query it was handed."""

    def get_tasks(**kwargs: Any) -> list[FakeTask]:
        asked.update(kwargs)
        return [FakeTask()]

    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(get_tasks=get_tasks)  # type: ignore[attr-defined]
    return module


def test_the_baseline_lookup_asks_clearml_for_the_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default baseline is the promoted model, not merely the last run to finish."""
    asked: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "clearml", _recording_clearml_module(asked))

    assert latest_completed_task_id("detection", tags=["prod"]) == TASK_ID
    assert asked["tags"] == ["prod"]
    assert asked["task_filter"]["status"] == ["completed", "published"]
    assert asked["task_filter"]["order_by"][0] == "-completed"


def test_a_task_name_matches_the_whole_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unanchored, 'yolo-v1' also matches 'yolo-v10', and the newest match would win."""
    asked: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "clearml", _recording_clearml_module(asked))

    latest_completed_task_id("detection", task_name="yolo-v1")
    assert asked["task_name"] == "^yolo-v1$"

    # A deliberate pattern still works, and an anchored one is not anchored twice.
    latest_completed_task_id("detection", task_name="yolo-v1.*")
    assert asked["task_name"] == "^yolo-v1.*$"
    latest_completed_task_id("detection", task_name="^exact$")
    assert asked["task_name"] == "^exact$"
    latest_completed_task_id("detection")
    assert asked["task_name"] is None


def test_no_promoted_model_is_reported_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(get_tasks=lambda **_: [])  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)

    assert latest_completed_task_id("detection", tags=["prod"]) is None


def test_automatic_baseline_excludes_the_current_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "b" * 32
    previous = "c" * 32
    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(  # type: ignore[attr-defined]
        get_tasks=lambda **_: [FakeTask(task_id=current), FakeTask(task_id=previous)]
    )
    monkeypatch.setitem(sys.modules, "clearml", module)

    assert latest_completed_task_id("detection", tags=["prod"], exclude_task_id=current) == previous


def test_current_invocation_is_the_only_match_reports_automatic_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "b" * 32
    module = types.ModuleType("clearml")
    module.Task = types.SimpleNamespace(  # type: ignore[attr-defined]
        get_tasks=lambda **_: [FakeTask(task_id=current)]
    )
    monkeypatch.setitem(sys.modules, "clearml", module)

    assert latest_completed_task_id("detection", exclude_task_id=current) is None


def test_task_ids_are_told_apart_from_checkpoint_names() -> None:
    assert looks_like_task_id(TASK_ID)
    assert not looks_like_task_id("yolo11n.pt")
    assert not looks_like_task_id("a" * 31)
    assert not looks_like_task_id("z" * 32)


def test_weights_selects_best_even_when_registered_before_other_models(
    patch_clearml: Any, tmp_path: Path
) -> None:
    """Registration order must not select an unmarked epoch checkpoint."""
    best = tmp_path / "checkpoint.pt"
    best.write_bytes(b"")
    patch_clearml(
        FakeTask(
            models={
                "output": [
                    FakeModel(str(best), checkpoint_role="best"),
                    FakeModel(str(tmp_path / "epoch1.pt")),
                ]
            }
        )
    )

    assert resolve_task_weights(TASK_ID) == best


def test_weights_reject_an_uploaded_checkpoint_artifact_without_a_best_output_model(
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

    with pytest.raises(ValueError, match="best Output Model"):
        resolve_task_weights(TASK_ID)


def test_weights_do_not_download_checkpoint_artifacts(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={
                "metrics_predictions": ExplodingArtifact(),
                "train_weights_best": ExplodingArtifact(),
            }
        )
    )

    with pytest.raises(ValueError, match="best Output Model"):
        resolve_task_weights(TASK_ID)


def test_filename_only_best_output_model_is_rejected(patch_clearml: Any, tmp_path: Path) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")
    patch_clearml(FakeTask(models={"output": [FakeModel(str(checkpoint))]}))

    with pytest.raises(ValueError, match="best Output Model"):
        resolve_task_weights(TASK_ID)


def test_a_task_without_a_checkpoint_says_so(patch_clearml: Any) -> None:
    patch_clearml(FakeTask())

    with pytest.raises(ValueError, match="best Output Model"):
        resolve_task_weights(TASK_ID)


def test_local_checkpoints_never_reach_clearml(tmp_path: Path) -> None:
    """A path that exists is used as-is, so predict works with no ClearML at all."""
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")

    assert resolve_weights(checkpoint) == checkpoint


def test_bare_model_downloads_use_cy_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert resolve_weights("yolo11n.pt") == tmp_path / ".cache/ultralytics/weights/yolo11n.pt"


def test_thresholds_come_from_validation_csv_as_plain_floats(
    patch_clearml: Any, tmp_path: Path
) -> None:
    path = tmp_path / "thresholds.csv"
    path.write_text("class_name,confidence\ncar,0.31\nvan,0.47\n")
    patch_clearml(FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(str(path))}))

    assert fetch_best_confidences(TASK_ID) == pytest.approx({"car": 0.31, "van": 0.47})


@pytest.mark.parametrize(
    "payload",
    [
        {"car": 0.25},
        '{"car": 0.25}',
        pytest.param(pd.Series({"car": 0.25}), id="series"),
        pytest.param(pd.DataFrame({"confidence": [0.25]}, index=["car"]), id="dataframe"),
    ],
)
def test_historical_threshold_payloads_are_rejected(patch_clearml: Any, payload: object) -> None:
    patch_clearml(
        FakeTask(artifacts={"metrics_best_confidences_test": FakeArtifact(payload=payload)})
    )

    with pytest.raises(ValueError, match=BEST_CONFIDENCES_VAL):
        fetch_best_confidences(TASK_ID)


def test_a_missing_threshold_artifact_names_the_current_artifact(patch_clearml: Any) -> None:
    patch_clearml(FakeTask())

    with pytest.raises(ValueError, match=BEST_CONFIDENCES_VAL):
        fetch_best_confidences(TASK_ID)


def test_ambiguous_native_best_models_fail(patch_clearml: Any, tmp_path: Path) -> None:
    patch_clearml(
        FakeTask(
            models={
                "output": [
                    FakeModel(str(tmp_path / "a" / "checkpoint.pt"), checkpoint_role="best"),
                    FakeModel(str(tmp_path / "b" / "checkpoint.pt"), checkpoint_role="best"),
                ]
            }
        )
    )
    with pytest.raises(ValueError, match=r"[Aa]mbiguous"):
        resolve_task_weights(TASK_ID)


def test_validation_csv_is_the_only_threshold_source(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "thresholds.csv"
    value = 0.12345678901234566
    path.write_text(f"class_name,confidence\n001,{value:.17g}\n")
    patch_clearml(
        FakeTask(
            artifacts={
                BEST_CONFIDENCES_VAL: FakeArtifact(str(path)),
                "metrics_best_confidences_test": FakeArtifact(payload={"001": 0.9}),
            }
        )
    )
    assert fetch_best_confidences(TASK_ID) == {"001": value}


def test_non_csv_current_threshold_artifact_is_rejected(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "thresholds.json"
    path.write_text('{"car": 0.9}')
    patch_clearml(
        FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(str(path), payload={"car": 0.9})})
    )

    with pytest.raises(ValueError, match="CSV"):
        fetch_best_confidences(TASK_ID)


@pytest.mark.parametrize(
    "contents",
    [
        "class_name,confidence\ncar,0.1\ncar,0.2\n",
        "class_name,confidence\ncar,nan\n",
        "class_name,confidence\ncar,1.2\n",
        "class_name,confidence\n,0.1\n",
    ],
)
def test_invalid_threshold_csv_fails_without_historical_fallback(
    patch_clearml: Any, tmp_path: Path, contents: str
) -> None:
    path = tmp_path / "thresholds.csv"
    path.write_text(contents)
    patch_clearml(
        FakeTask(
            artifacts={
                BEST_CONFIDENCES_VAL: FakeArtifact(str(path)),
                "metrics_best_confidences_test": FakeArtifact(payload={"car": 0.9}),
            }
        )
    )
    with pytest.raises(ValueError, match=r"threshold|confidence|class"):
        fetch_best_confidences(TASK_ID)
