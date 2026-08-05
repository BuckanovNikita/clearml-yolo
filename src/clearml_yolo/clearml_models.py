"""Fetch a previous run's checkpoint and thresholds back out of ClearML.

Every stage after training needs artefacts a *past* run produced: the comparison needs
the old model's weights, and scoring at frozen thresholds needs the confidences that
run calibrated. Both live on a ClearML task, and nothing else in the project reads them
back — the report stage pulls dashboards, but a dashboard is neither a checkpoint nor a
full-precision threshold table.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

BEST_CONFIDENCES_PREFIX = "best_confidences"
# ClearML ids are 32 lowercase hex characters. Recognising them by shape is what lets
# `weights=` accept either a checkpoint on disk or a task, without a second config key
# that could contradict the first.
TASK_ID_LENGTH = 32


def looks_like_task_id(value: str) -> bool:
    return len(value) == TASK_ID_LENGTH and all(
        character in "0123456789abcdef" for character in value.lower()
    )


def _task(task_id: str) -> Any:
    from clearml import Task

    task: Any = Task.get_task(task_id=task_id)
    if task is None:
        raise ValueError(f"No ClearML task with id {task_id!r}")
    return task


def latest_completed_task_id(
    project_name: str,
    task_name: str | None = None,
    tags: Sequence[str] | None = None,
) -> str | None:
    """The most recently finished task of a project carrying every one of ``tags``.

    ``task_name`` is matched the way ClearML matches it — as a partial expression, not an
    exact name — so anchor it with ``^…$`` when a project holds names that contain one
    another.
    """
    from clearml import Task

    tasks: list[Any] = Task.get_tasks(
        project_name=project_name,
        task_name=task_name,
        tags=list(tags) if tags else None,
        task_filter={"status": ["completed", "published"], "order_by": ["-last_update"]},
    )
    if not tasks:
        return None
    logger.info(
        "Latest completed task in {!r} tagged {}: {} ({})",
        project_name,
        list(tags) if tags else "(any)",
        tasks[0].id,
        tasks[0].name,
    )
    task_id: str = tasks[0].id
    return task_id


def _checkpoint_from_models(task: Any) -> str | None:
    """Take the last output model a task registered, which is ultralytics' best.pt.

    Ultralytics' own ClearML callback registers checkpoints as output models rather
    than artifacts, and registers more than one over a run — the last is the one that
    survived training.
    """
    # clearml ships no type information, so the model containers are opaque.
    models: Any = task.get_models()
    output: list[Any] = list(models.get("output") or [])
    if not output:
        return None
    local_copy: str | None = output[-1].get_local_copy()
    return local_copy


def _checkpoint_from_artifacts(task: Any) -> str | None:
    """Fall back to an uploaded .pt artifact, for tasks that saved one by hand."""
    for name, artifact in task.artifacts.items():
        local = Path(str(artifact.get_local_copy()))
        if local.suffix == ".pt":
            logger.info("Using artifact {!r} of task {} as the checkpoint", name, task.id)
            return str(local)
    return None


def resolve_task_weights(task_id: str) -> Path:
    """Download the checkpoint a ClearML task produced and return its local path."""
    task = _task(task_id)
    checkpoint = _checkpoint_from_models(task) or _checkpoint_from_artifacts(task)
    if checkpoint is None:
        raise ValueError(
            f"ClearML task {task_id} ({task.name}) registered no output model and uploaded "
            "no .pt artifact, so it carries no checkpoint to run. Point at the training task "
            "rather than a downstream stage, or pass a local path instead."
        )
    path = Path(checkpoint)
    if not path.is_file():
        raise FileNotFoundError(f"ClearML returned {path} for task {task_id}, but it is not a file")
    logger.info("Checkpoint of task {} ({}): {}", task_id, task.name, path)
    return path


def resolve_weights(weights: str | Path) -> Path:
    """Accept either a checkpoint on disk or a ClearML task id, and return a real file."""
    candidate = Path(weights)
    if candidate.exists():
        return candidate
    text = str(weights)
    if looks_like_task_id(text):
        return resolve_task_weights(text)
    # Bare model names such as "yolo11n.pt" are downloaded by ultralytics itself, so a
    # missing file is not necessarily an error here.
    return candidate


def _as_threshold_mapping(payload: Any) -> dict[str, float]:
    if isinstance(payload, pd.DataFrame):
        frame = payload if payload.shape[1] == 1 else payload.iloc[:, :1]
        return {str(name): float(value) for name, value in frame.iloc[:, 0].items()}
    if isinstance(payload, pd.Series):
        return {str(name): float(value) for name, value in payload.items()}
    if isinstance(payload, dict):
        return {str(name): float(value) for name, value in payload.items()}
    raise TypeError(f"Unsupported best_confidences artifact of type {type(payload).__name__}")


def fetch_best_confidences(task_id: str, split: str) -> dict[str, float]:
    """Read the per-class thresholds a task calibrated for one split.

    The dashboards round their thresholds for display, so scoring both models at their
    frozen production thresholds has to read this artifact instead: a rounded threshold
    silently rescores every class and shows up as a model difference that is not one.
    """
    task = _task(task_id)
    name = f"{BEST_CONFIDENCES_PREFIX}_{split}"
    artifact = task.artifacts.get(name)
    if artifact is None:
        raise ValueError(
            f"ClearML task {task_id} ({task.name}) has no {name!r} artifact. Run the metrics "
            f"stage for split {split!r} on that task, or supply thresholds explicitly."
        )

    payload: Any = artifact.get()
    if isinstance(payload, str):
        payload = json.loads(payload)
    thresholds = _as_threshold_mapping(payload)
    logger.info("Thresholds of task {} for split {!r}: {} classes", task_id, split, len(thresholds))
    return thresholds
