"""Native Ultralytics training with explicit artifact ownership."""

from __future__ import annotations

from datetime import UTC, datetime
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
    upload_artifact,
)
from clearml_yolo.run_identity import RUNS_ROOT, point_latest_at, resolve_run_dir, resolve_run_id

TRAIN_DIR = "detect"
CHECKPOINT = "{project}/{name}/weights/best.pt"


class TrainResult(BaseModel):
    weights: Path
    save_dir: Path
    effective_args: dict[str, Any] = Field(default_factory=dict)


def _project_of_this_run(project: str | None, task_name: str) -> Path:
    if project is not None:
        return Path(project).resolve()
    directory = resolve_run_dir(
        RUNS_ROOT, resolve_run_id(task_name, None, datetime.now(tz=UTC)), None
    )
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


def train(ultralytics: dict[str, Any], clearml: ClearMLConfig) -> TrainResult:
    """Pass native settings unchanged, except isolated default output routing."""
    from ultralytics.models import YOLO

    task = init_task(clearml, stage="train")
    expect_artifacts(
        task,
        [
            "training_model_reference",
            "train_effective_arguments",
            "train_output_location",
            "dataset_resolved_configuration",
            "train_weights_best.pt",
        ],
    )
    settings = dict(ultralytics)
    architecture = settings.pop("model", "yolo11n.pt")
    settings["project"] = str(_project_of_this_run(settings.get("project"), clearml.task_name))
    settings.setdefault("name", clearml.task_name)
    data = settings.get("data")
    if isinstance(data, (str, Path)) and (Path(data).is_file() or not task.running_locally()):
        settings["data"] = str(connect_config_file(task, "dataset_configuration", Path(data)))
    upload_artifact(
        task, "training_model_reference", sanitize_configuration({"model": architecture})
    )
    model = YOLO(architecture)
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
    _publish_training(task, directory)
    logger.info("Training checkpoint: {}", best)
    return TrainResult(weights=best, save_dir=directory, effective_args=effective)
