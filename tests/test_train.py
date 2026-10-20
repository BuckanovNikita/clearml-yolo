"""Native training forwards settings and reads actual parent-process outputs."""

import sys
import types
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.adapters.clearml.session import ClearMLConfig
from clearml_yolo.adapters.storage.dataset import PreparedDataset
from clearml_yolo.adapters.storage.dataset_export import DatasetFormat
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.train import TrainResult, train
from native_config_helpers import training_settings
from workflow_dependencies import patch_workflow
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@pytest.fixture(autouse=True)
def native_publication_boundary(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    monkeypatch.setattr(
        workflow_dependencies.tracking, "publish_training_parameters", lambda *a: None
    )
    # Load the real trainer boundary before individual tests substitute YOLO construction.
    from clearml_yolo.adapters.integrations import native_trainer  # noqa: F401

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.native_ddp_relay",
        lambda *a: nullcontext(types.SimpleNamespace(replay=lambda trainer: None)),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.finalize_native_model",
        lambda *a: None,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.record_run_configuration",
        lambda *a: None,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.register_ground_truth",
        lambda *a, **k: None,
    )


def test_missing_ground_truth_is_rejected_before_task_creation(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.init_task",
        lambda *_args, **_kwargs: pytest.fail("missing input must fail before task creation"),
    )
    with pytest.raises(TypeError, match="ground_truth"):
        train(training_settings(), ClearMLConfig(), deps=workflow_dependencies)  # type: ignore[call-arg]


def test_train_result_requires_prepared_dataset_paths(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        TrainResult(weights=tmp_path / "best.pt", save_dir=tmp_path)  # type: ignore[call-arg]


@pytest.mark.parametrize("dataset_format", ["ndjson", "flat"])
@pytest.mark.parametrize("device", ["cpu", [0, 1]])
@pytest.mark.parametrize("cache_identity", [None, "a" * 64])
def test_csv_training_uses_prepared_data_and_returns_cleaned_ground_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dataset_format: DatasetFormat,
    device: Any,
    cache_identity: str | None,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    expected_format = dataset_format
    prepared_dir = tmp_path / ".datasets" / "asked"
    data = prepared_dir / "data.yaml"
    cleaned = prepared_dir / "cleaned.csv"
    manifest = prepared_dir / "preparation.json"
    ndjson = prepared_dir / "dataset.ndjson"
    labels = prepared_dir / "labels.zip"
    for path in (data, cleaned, manifest, ndjson, labels):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("prepared\n", encoding="utf-8")
    alternate = tmp_path / "remote-data.yaml"
    alternate.write_text("remote\n", encoding="utf-8")
    calls: dict[str, Any] = {"uploads": [], "connections": [], "configurations": []}

    @contextmanager
    def cached_dataset(
        source: str | Path,
        cache_dir: Path,
        dataset_format: str = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> Iterator[PreparedDataset]:
        assert Path(source) == Path("source.csv")
        assert cache_dir == tmp_path / "cache"
        assert dataset_format == expected_format
        assert required_splits == ("train", "val", "test")
        calls["locked"] = True
        yield PreparedDataset(
            data=data,
            ground_truth=cleaned,
            manifest=manifest,
            dataset_format=expected_format,
            artifacts=[ndjson, labels],
            cache_identity=cache_identity,
        )
        calls["locked"] = False

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.cached_dataset",
        cached_dataset,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.record_run_configuration",
        lambda _task, values: calls["configurations"].append(values),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.init_task",
        lambda *args, **kwargs: object(),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.expect_artifacts",
        lambda *args, **kwargs: None,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.connect_config_file",
        lambda *args, **kwargs: calls["connections"].append((args, kwargs)) or alternate,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.register_ground_truth",
        lambda _task, truth, **kwargs: calls["uploads"].append((truth, kwargs["output_dir"])),
    )
    native_dir = tmp_path / "training" / "asked"
    (native_dir / "weights").mkdir(parents=True)
    (native_dir / "weights" / "best.pt").write_bytes(b"checkpoint")

    class Model:
        def __init__(self, _model: str) -> None:
            self.task = "detect"
            self.trainer = types.SimpleNamespace(
                save_dir=native_dir, args=types.SimpleNamespace(), data={}
            )

        def train(self, **kwargs: Any) -> None:
            from clearml_yolo.adapters.integrations.native_trainer import OwnedDetectionTrainer

            assert kwargs.pop("trainer") is OwnedDetectionTrainer
            assert calls["locked"]
            calls["native"] = kwargs
            self.trainer.args = types.SimpleNamespace(**kwargs)

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    result = train(
        ultralytics=training_settings()
        | {
            "model": "architecture.pt",
            "data": "stale.yaml",
            "device": device,
            "batch": -1,
            "amp": False,
            "compile": False,
            "project": str(tmp_path / "training"),
            "name": "asked",
        },
        clearml=ClearMLConfig(),
        ground_truth="source.csv",
        dataset_format=dataset_format,
        dataset_cache_dir=tmp_path / "cache",
        required_splits=["train", "val", "test"],
        deps=workflow_dependencies,
    )
    assert calls["native"]["data"] == str(data)
    assert calls["native"]["device"] == device
    assert calls["native"]["batch"] == -1
    assert calls["native"]["amp"] is False
    assert calls["native"]["compile"] is False
    assert calls["connections"][0][0][1:] == ("dataset", data)
    assert calls["connections"][0][1]["allow_remote_override"] is False
    assert calls["uploads"] == [(cleaned, tmp_path / "training")]
    assert calls["locked"] is False
    prepared_records = [
        values["prepared_dataset"]
        for values in calls["configurations"]
        if "prepared_dataset" in values
    ]
    assert prepared_records == (
        [{"cache_identity": cache_identity, "root": str(prepared_dir)}]
        if cache_identity is not None
        else []
    )
    assert result.weights == native_dir / "weights/best.pt"
    assert result.cleaned_ground_truth == cleaned
    assert result.dataset_reference == data


def test_csv_training_rejects_preparation_directory_outside_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.init_task",
        lambda *args, **kwargs: object(),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.expect_artifacts",
        lambda *args, **kwargs: None,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.cached_dataset",
        lambda *args, **kwargs: pytest.fail("escaped path must not reach dataset preparation"),
        raising=False,
    )
    with pytest.raises(ValueError, match="CY_HOME"):
        train(
            ultralytics=training_settings() | {"project": str(tmp_path), "name": "../outside"},
            clearml=ClearMLConfig(),
            ground_truth="source.csv",
            deps=workflow_dependencies,
        )


def test_training_has_no_implicit_model(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.init_task",
        lambda *args, **kwargs: object(),
    )
    with pytest.raises(ValueError, match="ultralytics\\.model"):
        train(
            training_settings(model=None),
            ClearMLConfig(),
            ground_truth="truth.csv",
            deps=workflow_dependencies,
        )


def test_csv_training_rejects_non_detection_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    import clearml_yolo.application.use_cases.train as training

    module = types.ModuleType("ultralytics.models")
    module.YOLO = lambda *args, **kwargs: types.SimpleNamespace(task="segment")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "ground_truth.csv",
        manifest=tmp_path / "preparation.json",
        dataset_format="ndjson",
        artifacts=[],
    )
    with pytest.raises(ValueError, match="detection model"):
        training._execute_training(
            types.SimpleNamespace(id="task"),
            "model.pt",
            training_settings(project=str(tmp_path), name="native", data=str(prepared.data)),
            prepared,
            deps=workflow_dependencies,
        )


def test_implicit_training_name_uses_active_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.application.use_cases import train as module

    task = SimpleNamespace(name="renamed/task", id="id", get_project_name=lambda: "project")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    patch_workflow(monkeypatch, workflow_dependencies, module, "init_task", lambda *a, **k: task)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        module,
        "expect_artifacts",
        lambda *a: None,
        raising=False,
    )

    def capture(
        _task: object, settings: dict[str, Any], *args: Any, deps: WorkflowDependencies
    ) -> Any:
        assert deps is workflow_dependencies
        assert settings["name"] == "renamed%2Ftask"
        assert settings["project"] == str(tmp_path / "runs/project/renamed%2Ftask-id/detect")
        raise RuntimeError("captured routing")

    patch_workflow(monkeypatch, workflow_dependencies, module, "_prepare_csv_dataset", capture)
    with pytest.raises(RuntimeError, match="captured routing"):
        train(
            training_settings(),
            ClearMLConfig(task_name="requested"),
            ground_truth="truth.csv",
            deps=workflow_dependencies,
        )


@pytest.mark.parametrize("explicit", [False, True])
def test_cache_cannot_live_inside_training_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    explicit: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from clearml_yolo.application.use_cases.train import _prepare_csv_dataset

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.cached_dataset",
        lambda *a, **k: pytest.fail("run-owned cache must be rejected before preparation"),
    )
    with (
        pytest.raises(ValueError, match="outside the run-owned training project"),
        _prepare_csv_dataset(
            types.SimpleNamespace(id="task"),
            {"project": str(tmp_path), "name": "train"},
            "source.csv",
            "ndjson",
            None,
            tmp_path / "cache" if explicit else None,
            deps=workflow_dependencies,
        ),
    ):
        pytest.fail("unsafe cache accepted")


def test_native_ddp_events_replay_before_model_finalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from clearml_yolo.application.use_cases.train import _execute_training

    events: list[str] = []
    directory = tmp_path / "train"
    (directory / "weights").mkdir(parents=True)
    (directory / "weights/best.pt").write_bytes(b"native checkpoint")

    class Model:
        def __init__(self, _architecture: object) -> None:
            self.task = "detect"
            self.trainer = types.SimpleNamespace(save_dir=directory)

        def train(self, **settings: Any) -> None:
            settings.pop("trainer")
            events.append("train")
            self.trainer.args = types.SimpleNamespace(**settings)

    @contextmanager
    def relay(_task: object, _model: object) -> Iterator[Any]:
        yield types.SimpleNamespace(replay=lambda _trainer: events.append("replay"))
        events.append("relay_closed")

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.native_ddp_relay",
        relay,
        raising=False,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.train.finalize_native_model",
        lambda *args: events.append("finalize"),
    )
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "ground_truth.csv",
        manifest=tmp_path / "preparation.json",
        dataset_format="ndjson",
        artifacts=[],
    )
    _execute_training(
        types.SimpleNamespace(id="task"),
        "model.pt",
        training_settings()
        | {"project": str(tmp_path), "name": "train", "data": str(prepared.data)},
        prepared,
        deps=workflow_dependencies,
    )
    assert events == ["train", "replay", "finalize", "relay_closed"]


@pytest.mark.parametrize(
    "selection", ["ultralytics", "rfdetr/small", "deimv2/s", "fasterrcnn/resnet50_fpn"]
)
def test_validated_general_is_published_before_any_dataset_preparation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    from clearml_yolo.application.use_cases import train as module
    from clearml_yolo.core.models import model_preset
    from clearml_yolo.entrypoints.composition import build_dependencies

    model = model_preset(selection)
    deps = build_dependencies(model)
    task = object()
    events: list[str] = []
    observed: list[dict[str, Any]] = []
    monkeypatch.setattr(deps.tracking, "init_task", lambda *a, **k: task)

    def publish(owner: object, values: dict[str, Any]) -> None:
        assert owner is task
        observed.append(values)
        events.append("General")

    def prepare(*args: Any, **kwargs: Any) -> Any:
        assert events == ["General"]
        raise RuntimeError("dataset reached after General")

    monkeypatch.setattr(deps.tracking, "publish_training_parameters", publish)
    monkeypatch.setattr(module, "_prepare_csv_dataset", prepare)
    settings = (
        training_settings()
        if selection == "ultralytics"
        else model.train.model_dump(mode="json") | {"model": model.preset}
    )
    settings.update(project=str(tmp_path), name="train", epochs=2, weight_decay=0.02)
    with pytest.raises(RuntimeError, match="dataset reached after General"):
        train(settings, ClearMLConfig(), "truth.csv", deps=deps)
    assert observed[0]["weight_decay"] == 0.02
    assert observed[0]["epochs"] == 2
    events.clear()
    with pytest.raises(ValueError, match="epochs"):
        train(settings | {"epochs": 0}, ClearMLConfig(), "truth.csv", deps=deps)
    assert events == []
