"""CSV-backed native training with one verified native best model."""

__all__ = ["TrainResult"]
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import (
    ClearMLConfig,
    DatasetFormat,
    PreparedDataset,
    TrainResult,
)
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies

TRAIN_DIR = "detect"


def _project_of_this_run(
    project: str | None, task: TaskHandle | None, *, deps: WorkflowDependencies
) -> Path:
    if project is not None:
        return deps.storage.resolve(deps.storage.write_path(project))
    directory = deps.storage.task_run_dir(
        deps.storage.runs_root(), *deps.tracking.task_identity(task)
    )
    deps.storage.mkdir(directory, parents=True, exist_ok=True)
    deps.storage.point_latest_at(deps.storage.runs_root(), directory)
    return directory / TRAIN_DIR


@contextmanager
def _prepare_csv_dataset(
    task: TaskHandle | None,
    settings: dict[str, Any],
    ground_truth: str | Path,
    dataset_format: DatasetFormat,
    required_splits: list[str] | None,
    dataset_cache_dir: str | Path | None,
    *,
    deps: WorkflowDependencies,
) -> Iterator[tuple[PreparedDataset, dict[str, Any]]]:
    if settings.get("resume"):
        raise ValueError("resume is unsupported with ground_truth; use model weights to fine-tune")
    project = deps.storage.resolve(Path(settings["project"]))
    output = deps.storage.resolve(project / str(settings["name"]))
    if output == project or not output.is_relative_to(project):
        raise ValueError("CSV training output directory must be inside its project")
    if deps.dataset.dataset_cache_root(dataset_cache_dir).is_relative_to(project):
        raise ValueError("dataset_cache_dir must be outside the run-owned training project")
    with deps.dataset.cached_dataset(
        ground_truth,
        dataset_cache_dir,
        dataset_format,
        required_splits=tuple(required_splits or ["train", "val"]),
    ) as prepared:
        deps.tracking.register_ground_truth(task, prepared.ground_truth, output_dir=project)
        effective, overrides = deps.dataset.apply_dataset_policy(settings, prepared.data)
        deps.tracking.record_run_configuration(task, {"training_data_overrides": overrides})
        deps.tracking.connect_config_file(
            task, "dataset", prepared.data, allow_remote_override=False
        )
        yield (prepared, effective)


def _execute_training(
    task: TaskHandle | None,
    architecture: str | Path,
    settings: dict[str, Any],
    prepared: PreparedDataset,
    *,
    deps: WorkflowDependencies,
) -> TrainResult:
    return deps.model.train(task, architecture, settings, prepared)


def train(
    ultralytics: dict[str, Any],
    clearml: ClearMLConfig,
    ground_truth: str | Path,
    ultralytics_predict: dict[str, Any] | None = None,
    dataset_format: DatasetFormat = "ndjson",
    required_splits: list[str] | None = None,
    dataset_cache_dir: str | Path | None = None,
    *,
    deps: WorkflowDependencies,
) -> TrainResult:
    """Train from CSV ground truth; native callbacks own training publications."""
    with deps.resources.trace_operation("workflow.train"):
        task = deps.tracking.init_task(clearml, stage="train")
        deps.model.stage_settings(ultralytics_predict or {}, "predict")
        settings = deps.model.execution_settings(ultralytics, "train")
        architecture = settings.pop("model")
        if not architecture:
            raise ValueError(
                "Set ultralytics.model explicitly; no training model fallback is provided"
            )
        settings["mode"] = "train"
        settings["project"] = str(_project_of_this_run(settings.get("project"), task, deps=deps))
        settings["name"] = settings.get("name") or deps.storage.safe_path_component(
            deps.tracking.task_identity(task)[1]
        )
        deps.storage.write_path(Path(settings["project"]) / str(settings["name"]))
        with _prepare_csv_dataset(
            task,
            settings,
            ground_truth,
            dataset_format,
            required_splits,
            dataset_cache_dir,
            deps=deps,
        ) as (prepared, effective):
            return _execute_training(task, architecture, effective, prepared, deps=deps)
