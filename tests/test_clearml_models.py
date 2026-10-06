"""Reading a previous run's checkpoint and thresholds back out of ClearML."""

import gzip
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
    source_model_links,
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

    def get_output_log_web_page(self) -> str:
        return "https://app.example/tasks/" + self.id

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
    assert asked["task_name"] == r"\A(?:yolo-v1)\Z(?![\s\S])"

    # A deliberate pattern still works, and an anchored one is not anchored twice.
    latest_completed_task_id("detection", task_name="yolo-v1.*")
    assert asked["task_name"] == r"\A(?:yolo-v1.*)\Z(?![\s\S])"
    latest_completed_task_id("detection", task_name="^exact$")
    assert asked["task_name"] == r"\A(?:^exact$)\Z(?![\s\S])"
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


def test_weights_recover_an_uploaded_checkpoint_artifact_without_output_models(
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


def test_weights_do_not_download_checkpoint_artifacts(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={
                "metrics_predictions": ExplodingArtifact(),
                "metrics_evaluation": ExplodingArtifact(),
            }
        )
    )

    with pytest.raises(ValueError, match="checkpoint"):
        resolve_task_weights(TASK_ID)


def test_filename_only_best_output_model_is_recovered(patch_clearml: Any, tmp_path: Path) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")
    patch_clearml(FakeTask(models={"output": [FakeModel(str(checkpoint))]}))

    assert resolve_task_weights(TASK_ID) == checkpoint


def test_a_task_without_a_checkpoint_says_so(patch_clearml: Any) -> None:
    patch_clearml(FakeTask())

    with pytest.raises(ValueError, match="checkpoint"):
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
def test_historical_threshold_payloads_are_recovered(patch_clearml: Any, payload: object) -> None:
    patch_clearml(
        FakeTask(artifacts={"metrics_best_confidences_test": FakeArtifact(payload=payload)})
    )

    assert fetch_best_confidences(TASK_ID) == {"car": 0.25}


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


def test_validation_csv_precedes_historical_threshold_source(
    patch_clearml: Any, tmp_path: Path
) -> None:
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


def test_json_current_threshold_artifact_is_recovered(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "thresholds.json"
    path.write_text('{"car": 0.9}')
    patch_clearml(
        FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(str(path), payload={"car": 0.9})})
    )

    assert fetch_best_confidences(TASK_ID) == {"car": 0.9}


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


def test_multiple_baseline_tags_use_all_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: dict[str, Any] = {}
    monkeypatch.setitem(sys.modules, "clearml", _recording_clearml_module(asked))
    latest_completed_task_id("detection", tags=["prod", "approved"])
    assert asked["tags"] == ["__$all", "prod", "approved"]


@pytest.mark.parametrize("name", ["best_confidences_val", "best_confidences_test"])
def test_unprefixed_threshold_aliases(patch_clearml: Any, name: str) -> None:
    patch_clearml(FakeTask(artifacts={name: FakeArtifact(payload={"001": 0.12345678901234566})}))
    assert fetch_best_confidences(TASK_ID) == {"001": 0.12345678901234566}


@pytest.mark.parametrize(
    "payload",
    [
        pd.Series([0.2], index=["001"]),
        pd.DataFrame({"value": [0.2]}, index=["001"]),
        '"{\\"001\\": 0.2}"',
    ],
)
def test_threshold_payload_encodings(patch_clearml: Any, payload: Any) -> None:
    patch_clearml(FakeTask(artifacts={"best_confidences_val": FakeArtifact(payload=payload)}))
    assert fetch_best_confidences(TASK_ID) == {"001": 0.2}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {" ": 0.1},
        {"car": float("inf")},
        {"car": -0.1},
        {"car": "no"},
        pd.Series([0.1, 0.2], index=["car", "car"]),
        pd.DataFrame({"other": [0.1], "metric": [0.2]}, index=["car"]),
    ],
)
def test_bad_preferred_threshold_prevents_fallback(patch_clearml: Any, payload: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={
                BEST_CONFIDENCES_VAL: FakeArtifact(payload=payload),
                "best_confidences_test": FakeArtifact(payload={"car": 0.9}),
            }
        )
    )
    with pytest.raises(ValueError, match=BEST_CONFIDENCES_VAL):
        fetch_best_confidences(TASK_ID)


@pytest.mark.parametrize(
    "name",
    [
        "metrics_dashboard_full_val",
        "dashboard_full_val",
        "metrics_dashboard_full_test",
        "dashboard_full_test",
    ],
)
def test_dashboard_payload_fallback(patch_clearml: Any, name: str) -> None:
    payload = pd.DataFrame({"confidence": [0.42], "recall": [0.8]}, index=["001"])
    patch_clearml(FakeTask(artifacts={name: FakeArtifact(payload=payload)}))
    assert fetch_best_confidences(TASK_ID) == {"001": 0.42}


@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_dashboard_file_fallback_preserves_class_ids(
    patch_clearml: Any, tmp_path: Path, suffix: str
) -> None:
    path = tmp_path / ("dashboard" + suffix)
    frame = pd.DataFrame({"confidence": [0.42], "recall": [0.8]}, index=["001"])
    if suffix == ".csv":
        frame.to_csv(path)
    else:
        frame.to_excel(path)
    patch_clearml(FakeTask(artifacts={"dashboard_full_test": FakeArtifact(str(path))}))
    assert fetch_best_confidences(TASK_ID) == {"001": 0.42}


def test_output_url_best_beats_registration_order(patch_clearml: Any, tmp_path: Path) -> None:
    best = tmp_path / "download.pt"
    best.touch()
    model = FakeModel(str(best))
    model.url = "https://files.example/nested/%62est.pt?download=1"
    patch_clearml(FakeTask(models={"output": [model, FakeModel("last.pt")]}))
    from clearml_yolo.clearml_models import resolve_task_model

    path, links = resolve_task_model(TASK_ID)
    assert path == best
    assert links["model_id"] == model.id
    assert links["model_url"] == model.url


def test_last_output_fallback(patch_clearml: Any, tmp_path: Path) -> None:
    last = tmp_path / "epoch.pt"
    last.touch()
    patch_clearml(FakeTask(models={"output": [FakeModel("first.pt"), FakeModel(str(last))]}))
    assert resolve_task_weights(TASK_ID) == last


def test_ambiguous_url_best_fails(patch_clearml: Any) -> None:
    patch_clearml(FakeTask(models={"output": [FakeModel("a/best.pt"), FakeModel("b/best.pt")]}))
    with pytest.raises(ValueError, match="Ambiguous"):
        resolve_task_weights(TASK_ID)


def test_artifact_priority_and_links(patch_clearml: Any, tmp_path: Path) -> None:
    best = tmp_path / "best.pt"
    best.touch()
    task = FakeTask(
        artifacts={
            "train_weights_best.pt": FakeArtifact(str(best)),
            "train_weights_best": ExplodingArtifact(),
            "model": ExplodingArtifact(),
        }
    )
    patch_clearml(task)
    from clearml_yolo.clearml_models import resolve_task_model

    path, links = resolve_task_model(TASK_ID)
    assert path == best
    assert links["artifact_name"] == "train_weights_best.pt"
    assert links["task_id"] == TASK_ID
    assert "model_id" not in links
    assert source_model_links(TASK_ID) == links


def test_output_models_prevent_artifact_fallback(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(
            models={"output": [FakeModel("missing.pt")]}, artifacts={"model": ExplodingArtifact()}
        )
    )
    with pytest.raises(FileNotFoundError):
        resolve_task_weights(TASK_ID)


def test_non_pt_checkpoint_is_rejected(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "model.bin"
    path.touch()
    patch_clearml(FakeTask(models={"output": [FakeModel(str(path), checkpoint_role="best")]}))
    with pytest.raises(ValueError, match=r"\.pt"):
        resolve_task_weights(TASK_ID)


def test_sorted_pt_artifact_fallback(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "a.pt"
    path.touch()
    patch_clearml(
        FakeTask(artifacts={"z.pt": ExplodingArtifact(), "a.pt": FakeArtifact(str(path))})
    )
    assert resolve_task_weights(TASK_ID) == path


@pytest.mark.parametrize(
    ("preferred", "other"),
    [
        ("metrics_best_confidences_val", "best_confidences_val"),
        ("best_confidences_val", "metrics_best_confidences_test"),
        ("metrics_best_confidences_test", "best_confidences_test"),
        ("best_confidences_test", "metrics_dashboard_full_val"),
        ("metrics_dashboard_full_val", "dashboard_full_val"),
        ("dashboard_full_val", "metrics_dashboard_full_test"),
        ("metrics_dashboard_full_test", "dashboard_full_test"),
    ],
)
def test_threshold_priority(patch_clearml: Any, preferred: str, other: str) -> None:
    payload = pd.DataFrame({"confidence": [0.21]}, index=["001"])
    patch_clearml(
        FakeTask(artifacts={other: ExplodingArtifact(), preferred: FakeArtifact(payload=payload)})
    )
    assert fetch_best_confidences(TASK_ID) == {"001": 0.21}


@pytest.mark.parametrize(
    "payload",
    [
        pd.DataFrame({"other": [0.2]}, index=["001"]),
        pd.DataFrame({"confidence": []}),
        pd.DataFrame({"confidence": [0.1, 0.2]}, index=["car", "car"]),
        pd.DataFrame({"confidence": [0.1]}, index=[""]),
        pd.DataFrame({"confidence": [float("nan")]}, index=["car"]),
    ],
)
def test_invalid_dashboard_prevents_fallback(patch_clearml: Any, payload: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={
                "metrics_dashboard_full_val": FakeArtifact(payload=payload),
                "dashboard_full_test": FakeArtifact(
                    payload=pd.DataFrame({"confidence": [0.9]}, index=["car"])
                ),
            }
        )
    )
    with pytest.raises(ValueError, match="metrics_dashboard_full_val"):
        fetch_best_confidences(TASK_ID)


@pytest.mark.parametrize(
    "contents",
    [
        "class_name,confidence\ncar,0.1\ncar,0.2\n",
        "class_name,recall\ncar,0.1\n",
        "class_name,confidence\n,0.1\n",
        "class_name,confidence\ncar,nan\n",
        "class_name,confidence\n",
    ],
)
def test_invalid_dashboard_csv_prevents_fallback(
    patch_clearml: Any, tmp_path: Path, contents: str
) -> None:
    path = tmp_path / "dashboard.csv"
    path.write_text(contents)
    patch_clearml(
        FakeTask(
            artifacts={
                "metrics_dashboard_full_val": FakeArtifact(str(path)),
                "dashboard_full_test": ExplodingArtifact(),
            }
        )
    )
    with pytest.raises(ValueError, match="metrics_dashboard_full_val"):
        fetch_best_confidences(TASK_ID)


def test_inaccessible_preferred_threshold_prevents_fallback(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={
                BEST_CONFIDENCES_VAL: ExplodingArtifact(),
                "dashboard_full_test": FakeArtifact(
                    payload=pd.DataFrame({"confidence": [0.9]}, index=["car"])
                ),
            }
        )
    )
    with pytest.raises(ValueError, match=BEST_CONFIDENCES_VAL):
        fetch_best_confidences(TASK_ID)


@pytest.mark.parametrize("payload", ['{"car": 0.1, "car": 0.2}', {"car": True}])
def test_ambiguous_or_boolean_threshold_payload_fails(patch_clearml: Any, payload: Any) -> None:
    patch_clearml(FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(payload=payload)}))
    with pytest.raises(ValueError, match=BEST_CONFIDENCES_VAL):
        fetch_best_confidences(TASK_ID)


@pytest.mark.parametrize(
    "name",
    ["train_weights_best.pt", "train_weights_best", "best.pt", "best", "model", "checkpoint"],
)
def test_all_checkpoint_aliases(patch_clearml: Any, tmp_path: Path, name: str) -> None:
    path = tmp_path / "download.pt"
    path.touch()
    patch_clearml(FakeTask(artifacts={name: FakeArtifact(str(path))}))
    assert resolve_task_weights(TASK_ID) == path


def test_failed_preferred_checkpoint_artifact_prevents_fallback(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(
            artifacts={"train_weights_best.pt": ExplodingArtifact(), "model": ExplodingArtifact()}
        )
    )
    with pytest.raises(ValueError, match=r"train_weights_best\.pt"):
        resolve_task_weights(TASK_ID)


def test_metadata_beats_ambiguous_best_urls(patch_clearml: Any, tmp_path: Path) -> None:
    path = tmp_path / "marked.pt"
    path.touch()
    patch_clearml(
        FakeTask(
            models={
                "output": [
                    FakeModel("a/best.pt"),
                    FakeModel("b/best.pt"),
                    FakeModel(str(path), checkpoint_role="best"),
                ]
            }
        )
    )
    assert resolve_task_weights(TASK_ID) == path


def test_atomic_checkpoint_provenance_snapshot(patch_clearml: Any, tmp_path: Path) -> None:
    from clearml_yolo.clearml_models import resolve_task_model

    class ChangingTask(FakeTask):
        @override
        def get_models(self) -> dict[str, list[FakeModel]]:
            models = super().get_models()
            self._models = {"output": [FakeModel("changed.pt")]}
            return models

    path = tmp_path / "selected.pt"
    path.touch()
    patch_clearml(ChangingTask(models={"output": [FakeModel(str(path), checkpoint_role="best")]}))
    selected, links = resolve_task_model(TASK_ID)
    assert selected == path
    assert links["model_id"] == "selected"


def test_dashboard_warning_records_precision_and_provenance(patch_clearml: Any) -> None:
    from loguru import logger

    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)), level="WARNING")
    try:
        patch_clearml(
            FakeTask(
                artifacts={
                    "dashboard_full_test": FakeArtifact(
                        payload=pd.DataFrame({"confidence": [0.2]}, index=["car"])
                    )
                }
            )
        )
        assert fetch_best_confidences(TASK_ID) == {"car": 0.2}
    finally:
        logger.remove(sink)
    assert any(
        "dashboard_full_test" in message and "precision" in message and "provenance" in message
        for message in messages
    )


def test_clearml_dataframe_gzip_preserves_ids_and_precision(
    patch_clearml: Any, tmp_path: Path
) -> None:
    path = tmp_path / "thresholds.csv.gz"
    value = 0.12345678901234566
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        stream.write(f",confidence\n001,{value:.17g}\n")
    patch_clearml(FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(str(path))}))
    assert fetch_best_confidences(TASK_ID) == {"001": value}


@pytest.mark.parametrize(
    ("preferred", "other"),
    [
        ("train_weights_best.pt", "train_weights_best"),
        ("train_weights_best", "best.pt"),
        ("best.pt", "best"),
        ("best", "model"),
        ("model", "checkpoint"),
        ("checkpoint", "a.pt"),
    ],
)
def test_checkpoint_alias_priority(
    patch_clearml: Any, tmp_path: Path, preferred: str, other: str
) -> None:
    path = tmp_path / "selected.pt"
    path.touch()
    patch_clearml(
        FakeTask(artifacts={other: ExplodingArtifact(), preferred: FakeArtifact(str(path))})
    )
    assert resolve_task_weights(TASK_ID) == path


def test_output_download_none_prevents_fallback(patch_clearml: Any) -> None:
    patch_clearml(
        FakeTask(models={"output": [FakeModel("")]}, artifacts={"model": ExplodingArtifact()})
    )
    with pytest.raises(ValueError, match="no local file"):
        resolve_task_weights(TASK_ID)


def test_output_download_error_prevents_fallback(patch_clearml: Any) -> None:
    class FailingModel(FakeModel):
        @override
        def get_local_copy(self) -> str:
            raise RuntimeError("remote unavailable")

    patch_clearml(
        FakeTask(
            models={"output": [FailingModel("selected.pt")]},
            artifacts={"model": ExplodingArtifact()},
        )
    )
    with pytest.raises(ValueError, match=r"selected.*remote unavailable"):
        resolve_task_weights(TASK_ID)


def test_threshold_csv_single_value_column_can_precede_class_column(
    patch_clearml: Any, tmp_path: Path
) -> None:
    path = tmp_path / "thresholds.csv"
    path.write_text("value,class_name\n0.12345678901234566,001\n")
    patch_clearml(FakeTask(artifacts={BEST_CONFIDENCES_VAL: FakeArtifact(str(path))}))
    assert fetch_best_confidences(TASK_ID) == {"001": 0.12345678901234566}


def test_checkpoint_download_failure_redacts_sdk_credentials(patch_clearml: Any) -> None:
    from loguru import logger

    class FailingModel(FakeModel):
        @override
        def get_local_copy(self) -> str:
            raise OSError(
                "download refused https://user:private-password@host/model?token=private-token"
            )

    patch_clearml(FakeTask(models={"output": [FailingModel("selected.pt")]}))
    messages: list[str] = []
    sink = logger.add(messages.append, level="DEBUG", format="{message}")
    try:
        with pytest.raises(ValueError, match="download refused") as caught:
            resolve_task_weights(TASK_ID)
    finally:
        logger.remove(sink)
    output = str(caught.value) + "".join(messages)
    assert "OSError" in output
    assert TASK_ID in output
    assert "private-password" not in output
    assert "private-token" not in output
    assert caught.value.__suppress_context__
