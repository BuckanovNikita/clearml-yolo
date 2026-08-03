"""ClearML task lifecycle shared by every app.

A single task is created per invocation and reused by all stages of the pipeline, so
that training scalars, prediction artifacts, per-split metrics and the comparison
reports all land on one experiment.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

CLEARML_TASK_ID_ENV = "CLEARML_TASK_ID"

# clearml ships no type information, so its Task is opaque to the type checker.
Task = Any


class ClearMLConfig(BaseModel):
    """Identity of the ClearML experiment this run belongs to."""

    enabled: bool = True
    project_name: str = "clearml-yolo"
    task_name: str = "yolo-run"
    task_type: str = "training"
    tags: list[str] = Field(default_factory=list)
    output_uri: str | bool | None = True
    continue_task_id: str | None = None
    reuse_last_task_id: bool = False


def resolve_task_name(config: ClearMLConfig, stage: str) -> str:
    """Name a stage-specific task, used only when a stage runs standalone."""
    return config.task_name if stage == "pipeline" else f"{config.task_name}/{stage}"


def init_task(config: ClearMLConfig, stage: str) -> Any:
    """Create or attach to the ClearML task for this run.

    Returns None when tracking is disabled. When a task already exists in this
    process (the pipeline created it, and a stage is now running inside it), that
    task is returned rather than creating a second experiment.
    """
    if not config.enabled:
        logger.info("ClearML tracking disabled")
        return None

    from clearml import Task

    current: Any = Task.current_task()
    if current is not None:
        logger.info("Reusing active ClearML task {} ({})", current.id, current.name)
        return current

    task: Any
    if config.continue_task_id:
        task = Task.get_task(task_id=config.continue_task_id)
        Task.init(
            continue_last_task=True,
            reuse_last_task_id=config.continue_task_id,
            auto_connect_frameworks={"pytorch": False, "matplotlib": False},
        )
        logger.info("Continuing ClearML task {} ({})", task.id, task.name)
    else:
        task = Task.init(
            project_name=config.project_name,
            task_name=resolve_task_name(config, stage),
            task_type=config.task_type,
            tags=config.tags or None,
            output_uri=config.output_uri,
            reuse_last_task_id=config.reuse_last_task_id,
            auto_connect_frameworks={"pytorch": False, "matplotlib": False},
        )
        logger.info(
            "ClearML task {} created: project={!r} name={!r}",
            task.id,
            config.project_name,
            resolve_task_name(config, stage),
        )

    # Ultralytics' DDP children are separate processes whose ClearML callback would
    # otherwise call Task.init() itself and create a second, disconnected experiment.
    os.environ[CLEARML_TASK_ID_ENV] = task.id
    return task


def upload_dataframe(task: Any, name: str, frame: Any) -> None:
    """Upload a DataFrame as a CSV artifact, tolerating disabled tracking."""
    if task is None:
        return
    task.upload_artifact(name=name, artifact_object=frame)
    logger.debug("Uploaded artifact {}", name)
