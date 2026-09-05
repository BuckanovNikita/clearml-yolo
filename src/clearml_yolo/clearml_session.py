"""ClearML task lifecycle shared by every app.

A single task is created per invocation and reused by all stages of the pipeline, so
that training scalars, prediction artifacts, per-split metrics and the comparison
reports all land on one experiment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, model_validator

CLEARML_TASK_ID_ENV = "CLEARML_TASK_ID"

# The run tag of the shared infrastructure, when this process runs under one: the
# project's own spelling first, the contract's second. A tagged run is an agent's or a CI
# job's, and its experiments belong in a project named after the tag so that the janitor
# finds them and nothing lands among the user's own runs.
RUN_TAG_ENV_VARS = ("CY_RUN_TAG", "INFRA_RUN_TAG")
DEFAULT_PROJECT_NAME = "clearml-yolo"

# clearml ships no type information, so its Task is opaque to the type checker.
Task = Any


def run_tag() -> str | None:
    """The run tag this process was started under, or None for a person's own run."""
    for name in RUN_TAG_ENV_VARS:
        tag = os.environ.get(name, "").strip()
        if tag:
            return tag
    return None


def tagged_project_name(tag: str) -> str:
    """The project a tagged run's experiments go to: ``<tag> <what>``, as the contract spells it."""
    return f"{tag} {DEFAULT_PROJECT_NAME}"


class ClearMLConfig(BaseModel):
    """Identity of the ClearML experiment this run belongs to."""

    enabled: bool = True
    project_name: str = DEFAULT_PROJECT_NAME
    task_name: str = "yolo-run"
    task_type: str = "training"
    tags: list[str] = Field(default_factory=list)
    output_uri: str | bool | None = True
    continue_task_id: str | None = None
    reuse_last_task_id: bool = False

    @model_validator(mode="after")
    def _a_tagged_run_lands_in_its_own_project(self) -> ClearMLConfig:
        """Send a tagged run's experiments to the tag's project, unless one was named.

        Decided here rather than where the task is created because the project is read in
        more than one place — the report and the comparison search it for a baseline — and
        a name derived at only one of them would have the run write to one project and look
        in another. ``project_name`` is taken as overridden whenever it differs from the
        default: hydra-zen passes every field explicitly, so absence cannot be told from the
        default any other way. The tag itself goes on every tagged run, named project or
        not, so that its experiments can be found by tag wherever they landed.
        """
        tag = run_tag()
        if tag is None:
            return self
        if self.project_name == DEFAULT_PROJECT_NAME:
            self.project_name = tagged_project_name(tag)
        if tag not in self.tags:
            self.tags = [*self.tags, tag]
        return self


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


def connect_config_file(task: Any, name: str, path: Path) -> Path:
    """Store a file the run is configured by on the task, and return the path to read.

    A ClearML *configuration object* rather than an artifact: artifacts are what a run
    produced, and this is what it was told to do. The file's whole text lands in the
    experiment's configuration tab, so the run is readable a year later without the machine
    it ran on.

    The return value is the path that must be read from here on, and it is not always the
    one passed in. A task cloned and run on an agent is handed ClearML's own copy of the
    file — that is what makes the clone reproduce this run rather than whatever now sits at
    that path — so ignoring the return value would quietly reintroduce the machine
    dependency this removes. With tracking disabled the path comes back unchanged.

    Values that are not primitives never survive the hyperparameters: ultralytics' own
    ClearML callback connects ``vars(trainer.args)``, and ClearML drops each entry it
    cannot store rather than warning. An albumentations pipeline is such a value, which is
    why it is connected here as the file it came from.
    """
    if task is None:
        return path
    stored = Path(task.connect_configuration(configuration=path, name=name))
    logger.info("Connected {} to ClearML as configuration {!r}", path, name)
    return stored


def upload_dataframe(task: Any, name: str, frame: Any) -> None:
    """Upload a DataFrame as a CSV artifact, tolerating disabled tracking."""
    if task is None:
        return
    task.upload_artifact(name=name, artifact_object=frame)
    logger.debug("Uploaded artifact {}", name)
