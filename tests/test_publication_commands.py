"""Command publication lifecycle and nested-owner suppression."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.publishing import NoOpPublisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.metrics import EvaluationConfig, MetricsResult


def test_worker_publication_is_disabled_without_reading_task_identity(tmp_path: Path) -> None:
    from clearml_yolo.tasks.publication import prepare_publisher, publish_results

    publisher = prepare_publisher(None, FiftyOneConfig(enabled=True))

    assert isinstance(publisher, NoOpPublisher)
    assert (
        publish_results(
            publisher,
            None,
            output_dir=tmp_path / "must-not-be-created",
            ground_truth=tmp_path / "missing.csv",
        )
        is None
    )
    assert not (tmp_path / "must-not-be-created").exists()


def test_validation_disables_nested_prediction_and_metrics_publication(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from clearml_yolo.tasks import val

    nested: list[FiftyOneConfig] = []
    predictions = tmp_path / "predictions.csv"
    expected = MetricsResult(output_dir=tmp_path / "metrics")
    monkeypatch.setattr(val, "init_task", lambda *_args, **_kwargs: SimpleNamespace(id="val-task"))

    def predict(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        assert set(kwargs["splits"]) == {"train", "val", "test"}
        nested.append(kwargs["fiftyone"])
        return SimpleNamespace(predictions=predictions)

    def metrics(*_args: Any, **kwargs: Any) -> MetricsResult:
        assert set(kwargs["splits"]) == {"train", "val", "test"}
        nested.append(kwargs["fiftyone"])
        return expected

    monkeypatch.setattr(val, "predict", predict)
    monkeypatch.setattr(val, "compute_metrics", metrics)

    result = val.validate(
        weights="best.pt",
        ground_truth=tmp_path / "truth.csv",
        output_dir=tmp_path,
        clearml=ClearMLConfig(),
        ultralytics={},
        evaluation=EvaluationConfig(),
    )

    assert result is expected
    assert len(nested) == 2
    assert all(not config.enabled for config in nested)


def test_remote_clone_replays_canonical_run_and_general(monkeypatch: Any) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.apps import common
    from native_config_helpers import training_settings

    config = OmegaConf.create(
        {"clearml": {}, "ground_truth": "local.csv", "ultralytics": training_settings()}
    )
    inputs: list[dict[str, Any]] = []
    executed: list[tuple[str, int]] = []

    class RemoteTask:
        @staticmethod
        def running_locally() -> bool:
            return False

        @staticmethod
        def connect(values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
            assert kwargs == {"name": "General", "ignore_remote_overrides": False}
            return values | {"epochs": 17}

    def replay(_task: Any, values: dict[str, Any]) -> dict[str, Any]:
        inputs.append(values)
        return values | {"ground_truth": "remote.csv", "comparison_status": "previous result"}

    def command(clearml: Any, ground_truth: str, ultralytics: dict[str, Any]) -> None:
        executed.append((ground_truth, ultralytics["epochs"]))

    monkeypatch.setattr(hydra, "main", lambda **kwargs: lambda fn: lambda: fn(config))
    monkeypatch.setattr(common, "native_runtime", nullcontext)
    monkeypatch.setattr(common, "invocation", lambda *_args: nullcontext(RemoteTask()))
    monkeypatch.setattr(common, "replay_configuration", replay)
    common.launch("train", command)

    assert executed == [("remote.csv", 17)]
    assert inputs == [{"clearml": {}, "ground_truth": "local.csv"}]


@pytest.mark.parametrize("stage", ["train", "pipeline"])
@pytest.mark.parametrize("explicit_route", [False, True])
def test_remote_clone_does_not_replay_previous_owner_output_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stage: str, explicit_route: bool
) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.apps import common
    from clearml_yolo.run_identity import safe_path_component, task_run_dir
    from clearml_yolo.tasks import train as training
    from clearml_yolo.tasks.pipeline import routed_native
    from native_config_helpers import training_settings

    project = tmp_path / "new-run" / "detect"
    requested = training_settings()
    if explicit_route:
        requested.update(project=str(project), name="train")
    config = OmegaConf.create({"clearml": {}, "ultralytics": requested})
    executed: list[dict[str, Any]] = []

    class RemoteTask:
        id = "clone-id"
        name = "clone/train"

        @staticmethod
        def get_project_name() -> str:
            return "project"

        @staticmethod
        def running_locally() -> bool:
            return False

        @staticmethod
        def connect(values: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
            # The SDK mutates this mapping with the source task's effective General.
            values.update(
                epochs=17,
                project="/previous/run/detect",
                name="previous-task",
                save_dir="/previous/run/detect/previous-task",
            )
            return values

    task = RemoteTask()

    def execute_training(
        _task: Any, _architecture: Any, settings: dict[str, Any], _prepared: Any
    ) -> Any:
        executed.append(settings)
        return None

    def command(clearml: Any, ultralytics: dict[str, Any]) -> None:
        if stage == "pipeline":
            executed.append(routed_native(ultralytics, project, "train"))
        else:
            training.train(ultralytics, ClearMLConfig())

    monkeypatch.setattr(hydra, "main", lambda **kwargs: lambda fn: lambda: fn(config))
    monkeypatch.setattr(common, "native_runtime", nullcontext)
    monkeypatch.setattr(common, "invocation", lambda *_args: nullcontext(task))
    monkeypatch.setattr(common, "replay_configuration", lambda _task, values: values)
    monkeypatch.setattr(training, "init_task", lambda *_args, **_kwargs: task)
    monkeypatch.setattr(training, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(training, "_execute_training", execute_training)
    common.launch(stage, command)

    assert len(executed) == 1
    actual = executed[0]
    assert actual["epochs"] == 17
    assert "save_dir" not in actual
    if stage == "pipeline" or explicit_route:
        assert actual["project"] == str(project)
        assert actual["name"] == "train"
    else:
        expected = task_run_dir(tmp_path / "runs", "project", task.name, task.id) / "detect"
        assert actual["project"] == str(expected)
        assert actual["name"] == safe_path_component(task.name)


@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("save_dir", [None, "explicit-output"])
def test_current_save_dir_override_reaches_pipeline_conflict_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, remote: bool, save_dir: str | None
) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.apps import common
    from clearml_yolo.tasks.pipeline import routed_native
    from native_config_helpers import training_settings

    config = OmegaConf.create(
        {"clearml": {}, "ultralytics": training_settings() | {"save_dir": save_dir}}
    )

    class Task:
        @staticmethod
        def running_locally() -> bool:
            return not remote

        @staticmethod
        def connect(values: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
            values.update(project="/old/detect", name="old", save_dir="/old/detect/old")
            return values

    def command(clearml: Any, ultralytics: dict[str, Any]) -> None:
        assert "save_dir" in ultralytics
        assert ultralytics["save_dir"] == save_dir
        routed_native(ultralytics, tmp_path / "detect", "train")

    monkeypatch.setattr(hydra, "main", lambda **kwargs: lambda fn: lambda: fn(config))
    monkeypatch.setattr(common, "native_runtime", nullcontext)
    monkeypatch.setattr(common, "invocation", lambda *_args: nullcontext(Task()))
    monkeypatch.setattr(common, "replay_configuration", lambda _task, values: values)
    with pytest.raises(ValueError, match="save_dir conflicts with pipeline run_dir"):
        common.launch("pipeline", command)
