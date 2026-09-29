"""Native Ultralytics training with explicit artifact ownership."""

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    sanitize_configuration,
    task_identity,
    upload_artifact,
)
from clearml_yolo.dataset import PreparedDataset, apply_dataset_policy, prepare_dataset
from clearml_yolo.dataset_export import DatasetFormat
from clearml_yolo.native_config import execution_settings, stage_settings, write_native_yaml
from clearml_yolo.run_identity import RUNS_ROOT, point_latest_at, safe_path_component, task_run_dir

TRAIN_DIR = "detect"


class TrainResult(BaseModel):
    weights: Path
    save_dir: Path
    effective_args: dict[str, Any] = Field(default_factory=dict)
    cleaned_ground_truth: Path | None = None
    dataset_reference: Path | None = None


def _project_of_this_run(project: str | None, task: Any) -> Path:
    if project is not None:
        return Path(project).resolve()
    directory = task_run_dir(RUNS_ROOT, *task_identity(task))
    directory.mkdir(parents=True, exist_ok=True)
    point_latest_at(RUNS_ROOT, directory)
    return directory / TRAIN_DIR


def _publish_training(task: Any, directory: Path) -> None:
    """Upload native outputs, excluding image-containing training/debug batches."""
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix not in {".pt", ".csv", ".png", ".jpg", ".yaml"}:
            continue
        if path.name.startswith(("train_batch", "val_batch")):
            continue
        name = "train_" + path.relative_to(directory).as_posix().replace("/", "_")
        if path.suffix == ".yaml":
            connect_config_file(task, name, path, allow_remote_override=False)
        else:
            upload_artifact(task, name, path)


def _publish_preparation(task: Any, prepared: PreparedDataset) -> None:
    """Publish only the known non-image preparation files."""
    upload_artifact(task, "dataset_preparation", prepared.manifest)
    upload_artifact(task, "dataset_ground_truth", prepared.ground_truth)
    for path in prepared.artifacts:
        if path in {prepared.data, prepared.ground_truth, prepared.manifest}:
            continue
        if path.suffix == ".ndjson":
            upload_artifact(task, "dataset_ndjson", path)
        elif path.suffix == ".zip":
            upload_artifact(task, "dataset_labels", path)
        else:
            raise ValueError(f"Unsupported prepared dataset artifact: {path}")


def _csv_artifact_names(dataset_format: DatasetFormat) -> list[str]:
    if dataset_format not in {"ndjson", "flat"}:
        raise ValueError("dataset_format must be one of: ndjson, flat")
    names = [
        "dataset_preparation",
        "dataset_ground_truth",
        "dataset_labels",
        "train_data_overrides",
    ]
    if dataset_format == "ndjson":
        names.append("dataset_ndjson")
    return names


def _preparation_directory(settings: dict[str, Any]) -> Path:
    root = (Path(settings["project"]) / ".datasets").resolve()
    directory = (root / str(settings["name"])).resolve()
    if directory == root or not directory.is_relative_to(root):
        raise ValueError("CSV training name must resolve inside its run-owned dataset directory")
    return directory


def _prepare_csv_dataset(
    task: Any,
    settings: dict[str, Any],
    ground_truth: str | Path,
    dataset_format: DatasetFormat,
    required_splits: list[str] | None,
) -> tuple[PreparedDataset, dict[str, Any]]:

    if settings.get("resume"):
        raise ValueError("resume is unsupported with ground_truth; use model weights to fine-tune")
    prepared = prepare_dataset(
        ground_truth,
        _preparation_directory(settings),
        dataset_format,
        required_splits=tuple(required_splits or ["train", "val"]),
    )
    _publish_preparation(task, prepared)
    if dataset_format == "ndjson":
        from ultralytics.data.converter import convert_ndjson_to_yolo

        # Explicit output ownership avoids the upstream global dataset cache. The
        # manifest resolves local images; no image URLs or HTTP server are needed.
        data = asyncio.run(
            convert_ndjson_to_yolo(
                prepared.data.with_name("dataset.ndjson"),
                output_path=prepared.data.parent / "native",
            )
        )
        prepared = prepared.model_copy(update={"data": Path(data)})
    effective, overrides = apply_dataset_policy(settings, prepared.data)
    upload_artifact(task, "train_data_overrides", sanitize_configuration(overrides))
    connect_config_file(task, "dataset_configuration", prepared.data, allow_remote_override=False)
    # The configuration adapter publishes a reproducible copy. It must never select an
    # alternate file for a CSV-owned run, including when a task is cloned remotely.
    effective["data"] = str(prepared.data)
    return prepared, effective


def train(
    ultralytics: dict[str, Any],
    clearml: ClearMLConfig,
    ultralytics_predict: dict[str, Any] | None = None,
    ground_truth: str | Path | None = None,
    dataset_format: DatasetFormat = "ndjson",
    required_splits: list[str] | None = None,
) -> TrainResult:
    """Pass native settings unchanged, except isolated default output routing."""
    task = init_task(clearml, stage="train")
    # Shared command configs include prediction overrides; they never affect training.
    stage_settings(ultralytics_predict or {}, "predict")
    settings = execution_settings(ultralytics, "train")
    architecture = settings.pop("model")
    if not architecture:
        raise ValueError("Set ultralytics.model explicitly; no training model fallback is provided")
    settings["mode"] = "train"
    settings["project"] = str(_project_of_this_run(settings.get("project"), task))
    settings["name"] = settings.get("name") or safe_path_component(task_identity(task)[1])
    expected = [
        "training_model_reference",
        "train_effective_arguments",
        "train_output_location",
        "dataset_resolved_configuration",
        "train_weights_best.pt",
    ]
    if ground_truth is not None:
        expected.extend(_csv_artifact_names(dataset_format))
    expect_artifacts(task, expected)
    prepared: PreparedDataset | None = None
    if ground_truth is not None:
        prepared, settings = _prepare_csv_dataset(
            task, settings, ground_truth, dataset_format, required_splits
        )
    else:
        data = settings.get("data")
        if isinstance(data, (str, Path)) and (Path(data).is_file() or not task.running_locally()):
            settings["data"] = str(connect_config_file(task, "dataset_configuration", Path(data)))
    upload_artifact(
        task, "training_model_reference", sanitize_configuration({"model": architecture})
    )
    # Creating the native run directory here would trigger Ultralytics name incrementation.
    write_native_yaml(
        Path(settings["project"]) / ".configs" / settings["name"] / "ultralytics.yaml",
        settings | {"model": architecture},
        "train",
    )
    from ultralytics.models import YOLO

    model = YOLO(architecture)
    if model.task != "detect":
        raise ValueError(
            f"ground_truth training requires a detection model; loaded task={model.task!r}"
        )
    requested = settings | {"model": architecture}
    requested_path = write_native_yaml(
        Path(settings["project"]) / ".configs" / settings["name"] / "ultralytics_requested.yaml",
        requested,
        "train",
    )
    expect_artifacts(task, ["ultralytics_requested"])
    connect_config_file(task, "ultralytics_requested", requested_path, allow_remote_override=False)
    model.train(**settings)
    # Native DDP returns no validator result in its parent; trainer.save_dir still owns outputs.
    trainer: Any = model.trainer
    upload_artifact(task, "dataset_resolved_configuration", sanitize_configuration(trainer.data))
    directory = Path(trainer.save_dir)
    best = directory / "weights" / "best.pt"
    if not best.is_file():
        raise FileNotFoundError(f"Training finished without required checkpoint {best}")
    effective = dict(vars(trainer.args))
    upload_artifact(task, "train_effective_arguments", sanitize_configuration(effective))
    upload_artifact(task, "train_output_location", {"save_dir": str(directory)})
    config_path = write_native_yaml(
        directory / "ultralytics.yaml",
        settings | effective | {"model": architecture, "mode": "train"},
        "train",
    )
    expect_artifacts(task, ["ultralytics"])
    connect_config_file(task, "ultralytics", config_path, allow_remote_override=False)
    _publish_training(task, directory)
    logger.info("Training checkpoint: {}", best)
    return TrainResult(
        weights=best,
        save_dir=directory,
        effective_args=effective,
        cleaned_ground_truth=prepared.ground_truth if prepared is not None else None,
        dataset_reference=prepared.data if prepared is not None else None,
    )
