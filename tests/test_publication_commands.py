"""Command publication lifecycle and nested-owner suppression."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml.session import ClearMLConfig
from clearml_yolo.adapters.fiftyone.noop import NoOpPublisher
from clearml_yolo.adapters.storage.dataset import PreparedDataset
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.metrics import EvaluationConfig, MetricsResult
from clearml_yolo.core.publication import FiftyOneConfig
from workflow_dependencies import patch_workflow
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


def test_worker_publication_is_disabled_without_reading_task_identity(
    tmp_path: Path, workflow_dependencies: WorkflowDependencies
) -> None:
    from clearml_yolo.application.use_cases.publication import prepare_publisher, publish_results

    publisher = prepare_publisher(None, FiftyOneConfig(enabled=True), deps=workflow_dependencies)
    assert isinstance(publisher, NoOpPublisher)
    assert (
        publish_results(
            publisher,
            None,
            output_dir=tmp_path / "must-not-be-created",
            ground_truth=tmp_path / "missing.csv",
            deps=workflow_dependencies,
        )
        is None
    )
    assert not (tmp_path / "must-not-be-created").exists()


@pytest.fixture
def publication_dataset(tmp_path: Path) -> PreparedDataset:
    cache = tmp_path / "cache"
    cache.mkdir()
    data = cache / "dataset.yaml"
    data.write_text("names: [widget]\ntrain: images/train\nval: images/val\n")
    truth = cache / "cleaned.csv"
    truth.write_text("image_name,split\nexample.jpg,val\n")
    manifest = cache / "preparation.json"
    manifest.write_text('{"dataset_format":"flat"}\n')
    local_archive = cache / "labels.zip"
    local_archive.write_bytes(b"local dataset diagnostics")
    return PreparedDataset(
        data=data,
        ground_truth=truth,
        manifest=manifest,
        dataset_format="flat",
        artifacts=[local_archive],
    )


def test_training_policy_normalization_and_receipts_stay_out_of_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    publication_dataset: PreparedDataset,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from collections.abc import Iterator
    from contextlib import contextmanager, nullcontext
    from datetime import UTC, datetime

    import clearml
    import ultralytics.models

    from clearml_yolo.adapters.clearml.results import register_ground_truth
    from clearml_yolo.adapters.clearml.session import invocation
    from clearml_yolo.application.use_cases import train as training
    from clearml_yolo.application.use_cases.publication import publish_results
    from clearml_yolo.core import artifact_names
    from clearml_yolo.core.publication import PublicationReceipt, PublicationRequest
    from native_config_helpers import training_settings
    from test_clearml_session import FakeTask

    task = FakeTask()
    patch_workflow(monkeypatch, workflow_dependencies, clearml.Task, "init", lambda **_kwargs: task)
    patch_workflow(
        monkeypatch, workflow_dependencies, clearml.Task, "get_task", lambda **_kwargs: task
    )
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    prepared = publication_dataset
    truth = prepared.ground_truth

    @contextmanager
    def dataset(*_args: Any, **_kwargs: Any) -> Iterator[PreparedDataset]:
        yield prepared

    native_output = tmp_path / "native"
    (native_output / "weights").mkdir(parents=True)
    best = native_output / "weights" / "best.pt"
    best.write_bytes(b"best")

    class Model:
        task = "detect"

        def __init__(self, _architecture: str) -> None:
            self.trainer = SimpleNamespace(save_dir=native_output)

        def train(self, **settings: Any) -> None:
            assert not (Path(settings["project"]) / settings["name"]).exists()
            assert settings["fraction"] == 1.0
            assert settings["classes"] is None
            self.trainer.args = SimpleNamespace(**settings | {"batch": 8})

    receipt = PublicationReceipt(
        dataset_name="model-performance",
        task_id=task.id,
        run_key="evaluation",
        ground_truth_sha256="truth",
        source_ground_truth_sha256="truth",
        dataset_reused=False,
        sample_count=1,
        fields={"predictions": "candidate"},
        dataset_complete=True,
        run_complete=True,
        payload_paths={"ground_truth": truth},
        published_at=datetime.now(UTC),
    )

    class Publisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, request: PublicationRequest) -> PublicationReceipt:
            assert request.task_id == task.id
            assert request.ground_truth == truth
            return receipt

    patch_workflow(monkeypatch, workflow_dependencies, training, "cached_dataset", dataset)
    patch_workflow(monkeypatch, workflow_dependencies, ultralytics.models, "YOLO", Model)
    patch_workflow(
        monkeypatch, workflow_dependencies, training, "finalize_native_model", lambda *_args: None
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        training,
        "native_ddp_relay",
        lambda *_args: nullcontext(SimpleNamespace(replay=lambda _trainer: None)),
    )
    with invocation(ClearMLConfig(), "train"):
        result = training.train(
            training_settings()
            | {
                "model": "architecture.yaml",
                "project": str(tmp_path / "training"),
                "name": "detector",
                "fraction": 0.5,
                "classes": [0],
                "batch": -1,
            },
            ClearMLConfig(),
            ground_truth="source.csv",
            dataset_cache_dir=prepared.data.parent,
            deps=workflow_dependencies,
        )
        register_ground_truth(task, truth, output_dir=tmp_path / "publication")
        assert task.uploads == []
        assert (
            publish_results(
                Publisher(),
                task,
                output_dir=tmp_path / "publication",
                ground_truth=truth,
                deps=workflow_dependencies,
            )
            == receipt
        )
    assert result.weights == best
    assert [item["name"] for item in task.uploads] == [artifact_names.GROUND_TRUTH]
    run = next(
        item["configuration"] for item in reversed(task.configurations) if item["name"] == "run"
    )
    assert run["training_data_overrides"]["fraction"] == {"requested": 0.5, "effective": 1.0}
    assert run["training_data_overrides"]["classes"] == {"requested": [0], "effective": None}
    assert run["training_normalization"]["batch"] == {"requested": -1, "effective": 8}
    assert run["fiftyone_result"]["dataset_name"] == receipt.dataset_name
    assert (tmp_path / "publication" / "fiftyone_publication.json").is_file()
    assert prepared.manifest.is_file()
    assert prepared.artifacts[0].is_file()
    assert (native_output / "ultralytics.yaml").is_file()


def test_validation_disables_nested_prediction_and_metrics_publication(
    tmp_path: Path, monkeypatch: Any, workflow_dependencies: WorkflowDependencies
) -> None:
    from clearml_yolo.application.use_cases import val

    nested: list[FiftyOneConfig] = []
    predictions = tmp_path / "predictions.csv"
    expected = MetricsResult(output_dir=tmp_path / "metrics")
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        val,
        "init_task",
        lambda *_args, **_kwargs: SimpleNamespace(id="val-task"),
    )

    def predict(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        assert set(kwargs["splits"]) == {"train", "val", "test"}
        nested.append(kwargs["fiftyone"])
        return SimpleNamespace(predictions=predictions)

    def metrics(*_args: Any, **kwargs: Any) -> MetricsResult:
        assert set(kwargs["splits"]) == {"train", "val", "test"}
        nested.append(kwargs["fiftyone"])
        return expected

    patch_workflow(monkeypatch, workflow_dependencies, val, "predict", predict)
    patch_workflow(monkeypatch, workflow_dependencies, val, "compute_metrics", metrics)
    result = val.validate(
        weights="best.pt",
        ground_truth=tmp_path / "truth.csv",
        output_dir=tmp_path,
        clearml=ClearMLConfig(),
        ultralytics={},
        evaluation=EvaluationConfig(),
        deps=workflow_dependencies,
    )
    assert result is expected
    assert len(nested) == 2
    assert all(not config.enabled for config in nested)


def test_remote_clone_replays_canonical_run_and_general(
    monkeypatch: Any, workflow_dependencies: WorkflowDependencies
) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.entrypoints.hydra import common
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

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        hydra,
        "main",
        lambda **kwargs: lambda fn: lambda: fn(config),
    )
    patch_workflow(monkeypatch, workflow_dependencies, common, "native_runtime", nullcontext)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        common,
        "invocation",
        lambda *_args, **_kwargs: nullcontext(RemoteTask()),
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, common, "initialize_naming", lambda _task: None
    )
    patch_workflow(monkeypatch, workflow_dependencies, common, "replay_configuration", replay)
    common.launch("train", command)
    assert executed == [("remote.csv", 17)]
    assert inputs == [{"clearml": {}, "ground_truth": "local.csv"}]


@pytest.mark.parametrize("stage", ["train", "pipeline"])
@pytest.mark.parametrize("explicit_route", [False, True])
def test_remote_clone_does_not_replay_previous_owner_output_route(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
    explicit_route: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.adapters.storage.run_identity import safe_path_component, task_run_dir
    from clearml_yolo.application.use_cases import train as training
    from clearml_yolo.application.use_cases.pipeline import routed_native
    from clearml_yolo.entrypoints.hydra import common
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
            values.update(
                epochs=17,
                project="/previous/run/detect",
                name="previous-task",
                save_dir="/previous/run/detect/previous-task",
            )
            return values

    task = RemoteTask()

    def execute_training(
        _task: Any,
        _architecture: Any,
        settings: dict[str, Any],
        _prepared: Any,
        *,
        deps: WorkflowDependencies,
    ) -> Any:
        executed.append(settings)
        return None

    def command(clearml: Any, ultralytics: dict[str, Any]) -> None:
        if stage == "pipeline":
            executed.append(routed_native(ultralytics, project, "train"))
        else:
            training.train(
                ultralytics, ClearMLConfig(), ground_truth="truth.csv", deps=workflow_dependencies
            )

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        hydra,
        "main",
        lambda **kwargs: lambda fn: lambda: fn(config),
    )
    patch_workflow(monkeypatch, workflow_dependencies, common, "native_runtime", nullcontext)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        common,
        "invocation",
        lambda *_args, **_kwargs: nullcontext(task),
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, common, "initialize_naming", lambda _task: None
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        common,
        "replay_configuration",
        lambda _task, values: values,
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, training, "init_task", lambda *_args, **_kwargs: task
    )
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        training,
        "_prepare_csv_dataset",
        lambda _task, settings, *_args, **_kwargs: nullcontext((object(), settings)),
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, training, "_execute_training", execute_training
    )
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    remote: bool,
    save_dir: str | None,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from contextlib import nullcontext

    import hydra
    from omegaconf import OmegaConf

    from clearml_yolo.application.use_cases.pipeline import routed_native
    from clearml_yolo.entrypoints.hydra import common
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

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        hydra,
        "main",
        lambda **kwargs: lambda fn: lambda: fn(config),
    )
    patch_workflow(monkeypatch, workflow_dependencies, common, "native_runtime", nullcontext)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        common,
        "invocation",
        lambda *_args, **_kwargs: nullcontext(Task()),
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, common, "initialize_naming", lambda _task: None
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        common,
        "replay_configuration",
        lambda _task, values: values,
    )
    with pytest.raises(ValueError, match="save_dir conflicts with pipeline run_dir"):
        common.launch("pipeline", command)


def test_real_invocation_freezes_routing_before_collision_display_rename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workflow_dependencies: WorkflowDependencies
) -> None:
    from contextlib import nullcontext

    import clearml
    from omegaconf import OmegaConf

    from clearml_yolo.adapters.clearml.session import task_identity
    from clearml_yolo.adapters.storage.run_identity import task_run_dir
    from clearml_yolo.entrypoints.hydra import common
    from test_clearml_session import FakeTask

    class Task(FakeTask):
        project = "project-id"

        @staticmethod
        def get_project_name() -> str:
            return "project"

        def set_name(self, name: str) -> None:
            self.name = name

    task = Task()
    task.name = "requested/report"
    patch_workflow(monkeypatch, workflow_dependencies, clearml.Task, "init", lambda **_kwargs: task)
    patch_workflow(
        monkeypatch, workflow_dependencies, clearml.Task, "get_task", lambda **_kwargs: task
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        clearml.Task,
        "query_tasks",
        lambda **_kwargs: [
            {"id": "previous-task", "project": task.project, "name": "requested/report"},
            {"id": task.id, "project": task.project, "name": task.name},
        ],
    )
    patch_workflow(monkeypatch, workflow_dependencies, common, "native_runtime", nullcontext)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    outputs: list[str | None] = []

    def command(clearml: Any, output_dir: str | None) -> None:
        outputs.append(output_dir)
        assert task_identity(task) == ("project", "requested/report", task.id)

    common.execute_owned(
        "report",
        OmegaConf.create({"clearml": ClearMLConfig().model_dump(), "output_dir": None}),
        command,
    )
    assert task.name.startswith("requested/report-")
    expected = task_run_dir(tmp_path / "runs", "project", "requested/report", task.id) / "report"
    assert outputs == [str(expected)]
    run = next(
        item["configuration"] for item in reversed(task.configurations) if item["name"] == "run"
    )
    assert run["display_names"]["requested_task_name"] == "requested/report"
    assert run["display_names"]["effective_task_name"] == task.name
    assert run["clearml"]["task_name"] == ClearMLConfig().task_name
    assert task.completed
