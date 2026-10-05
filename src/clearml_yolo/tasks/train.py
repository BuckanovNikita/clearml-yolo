"""CSV-backed native training with one verified native best model."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo.clearml_native import finalize_native_model
from clearml_yolo.clearml_results import register_ground_truth
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    init_task,
    record_run_configuration,
    task_identity,
)
from clearml_yolo.dataset import PreparedDataset, apply_dataset_policy
from clearml_yolo.dataset_cache import cached_dataset, dataset_cache_root
from clearml_yolo.dataset_export import DatasetFormat
from clearml_yolo.filesystem import model_weights_path, runs_root, write_path
from clearml_yolo.native_config import (
    execution_settings,
    requested_settings,
    stage_settings,
    write_native_yaml,
)
from clearml_yolo.native_ddp import native_ddp_relay
from clearml_yolo.run_identity import point_latest_at, safe_path_component, task_run_dir

TRAIN_DIR = "detect"


class TrainResult(BaseModel):
    weights: Path
    save_dir: Path
    effective_args: dict[str, Any] = Field(default_factory=dict)
    cleaned_ground_truth: Path
    dataset_reference: Path


def _project_of_this_run(project: str | None, task: Any) -> Path:
    if project is not None:
        return write_path(project).resolve()
    directory = task_run_dir(runs_root(), *task_identity(task))
    directory.mkdir(parents=True, exist_ok=True)
    point_latest_at(runs_root(), directory)
    return directory / TRAIN_DIR


@contextmanager
def _prepare_csv_dataset(
    task: Any,
    settings: dict[str, Any],
    ground_truth: str | Path,
    dataset_format: DatasetFormat,
    required_splits: list[str] | None,
    dataset_cache_dir: str | Path | None,
) -> Iterator[tuple[PreparedDataset, dict[str, Any]]]:
    if settings.get("resume"):
        raise ValueError("resume is unsupported with ground_truth; use model weights to fine-tune")
    project = Path(settings["project"]).resolve()
    output = (project / str(settings["name"])).resolve()
    if output == project or not output.is_relative_to(project):
        raise ValueError("CSV training output directory must be inside its project")
    if dataset_cache_root(dataset_cache_dir).is_relative_to(project):
        raise ValueError("dataset_cache_dir must be outside the run-owned training project")
    with cached_dataset(
        ground_truth,
        dataset_cache_dir,
        dataset_format,
        required_splits=tuple(required_splits or ["train", "val"]),
    ) as prepared:
        register_ground_truth(task, prepared.ground_truth, output_dir=project)
        effective, overrides = apply_dataset_policy(settings, prepared.data)
        record_run_configuration(task, {"training_data_overrides": overrides})
        connect_config_file(task, "dataset", prepared.data, allow_remote_override=False)
        yield prepared, effective


def _execute_training(
    task: Any, architecture: str | Path, settings: dict[str, Any], prepared: PreparedDataset
) -> TrainResult:
    from ultralytics.models import YOLO

    model = YOLO(model_weights_path(architecture))
    if model.task != "detect":
        raise ValueError(f"Training requires a detection model; loaded task={model.task!r}")
    requested = requested_settings(settings, "train") | {"model": str(architecture)}
    write_native_yaml(
        Path(settings["project"]) / ".configs" / settings["name"] / "ultralytics_requested.yaml",
        requested,
        "train",
    )
    with native_ddp_relay(task, model) as relay:
        model.train(**settings)
        trainer: Any = model.trainer
        relay.replay(trainer)
        directory = Path(trainer.save_dir)
        best = directory / "weights" / "best.pt"
        if not best.is_file():
            raise FileNotFoundError(f"Training finished without required checkpoint {best}")
        effective = dict(vars(trainer.args))
        write_native_yaml(directory / "ultralytics.yaml", requested | effective, "train")
        differences = {
            key: {"requested": requested.get(key), "effective": value}
            for key, value in effective.items()
            if requested.get(key) != value
        }
        record_run_configuration(task, {"training_normalization": differences})
        finalize_native_model(task, model, trainer, architecture)
        logger.info("Training checkpoint: {}", best)
        return TrainResult(
            weights=best,
            save_dir=directory,
            effective_args=effective,
            cleaned_ground_truth=prepared.ground_truth,
            dataset_reference=prepared.data,
        )


def train(
    ultralytics: dict[str, Any],
    clearml: ClearMLConfig,
    ground_truth: str | Path,
    ultralytics_predict: dict[str, Any] | None = None,
    dataset_format: DatasetFormat = "ndjson",
    required_splits: list[str] | None = None,
    dataset_cache_dir: str | Path | None = None,
) -> TrainResult:
    """Train from CSV ground truth; native callbacks own training publications."""
    task = init_task(clearml, stage="train")
    stage_settings(ultralytics_predict or {}, "predict")
    settings = execution_settings(ultralytics, "train")
    architecture = settings.pop("model")
    if not architecture:
        raise ValueError("Set ultralytics.model explicitly; no training model fallback is provided")
    settings["mode"] = "train"
    settings["project"] = str(_project_of_this_run(settings.get("project"), task))
    settings["name"] = settings.get("name") or safe_path_component(task_identity(task)[1])
    write_path(Path(settings["project"]) / str(settings["name"]))
    with _prepare_csv_dataset(
        task, settings, ground_truth, dataset_format, required_splits, dataset_cache_dir
    ) as (prepared, effective):
        return _execute_training(task, architecture, effective, prepared)
