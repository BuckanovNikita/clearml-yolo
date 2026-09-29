"""Fetch a previous run's checkpoint and thresholds back out of ClearML.

Every stage after training needs artefacts a *past* run produced: the comparison needs
the old model's weights, and scoring at frozen thresholds needs the confidences that
run calibrated. Both live on a ClearML task, and nothing else in the project reads them
back — the report stage pulls dashboards, but a dashboard is neither a checkpoint nor a
full-precision threshold table.
"""

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pandas as pd
from loguru import logger

from clearml_yolo.artifact_names import BEST_CONFIDENCES_PREFIX, per_split

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


def _anchored(task_name: str | None) -> str | None:
    """Pin a name to the whole task name, leaving an already-anchored pattern alone."""
    if not task_name:
        return None
    start = task_name if task_name.startswith("^") else f"^{task_name}"
    return start if start.endswith("$") else f"{start}$"


def latest_completed_task_id(
    project_name: str,
    task_name: str | None = None,
    tags: Sequence[str] | None = None,
    exclude_task_id: str | None = None,
) -> str | None:
    """The most recently finished task of a project carrying every one of ``tags``.

    ``task_name`` is anchored before it is sent. ClearML matches it as a regular
    expression against any part of the name, so an unanchored ``yolo-v1`` also matches
    ``yolo-v10`` — and since the newest match wins, asking for one model can silently
    return a different one. Anchoring leaves deliberate patterns working: pass
    ``yolo-v1.*`` to get the old behaviour back.
    """
    from clearml import Task

    tasks: list[Any] = Task.get_tasks(
        project_name=project_name,
        task_name=_anchored(task_name),
        tags=list(tags) if tags else None,
        task_filter={
            "status": ["completed", "published"],
            "order_by": ["-completed", "-last_update"],
        },
    )
    selected = next((task for task in tasks if task.id != exclude_task_id), None)
    if selected is None:
        return None
    logger.info(
        "Latest completed task in {!r} tagged {}: {} ({})",
        project_name,
        list(tags) if tags else "(any)",
        selected.id,
        selected.name,
    )
    task_id: str = selected.id
    return task_id


def best_output_model(task: Any) -> Any | None:
    """Select explicitly marked best weights, independent of registration order."""
    outputs: list[Any] = list(task.get_models().get("output") or [])
    candidates = [
        model
        for model in outputs
        if model.get_metadata("clearml_yolo_checkpoint_role") == "best"
        or Path(unquote(urlsplit(str(model.url or "")).path)).name == "best.pt"
    ]
    if len(candidates) > 1:
        raise ValueError(f"Ambiguous best output models on ClearML task {task.id}")
    return candidates[0] if candidates else None


def _checkpoint_from_models(task: Any) -> str | None:
    model = best_output_model(task)
    if model is None:
        return None
    local_copy: str | None = model.get_local_copy()
    return local_copy


def source_model_links(task_id: str) -> dict[str, str]:
    """Record source identity and links without copying source training parameters."""
    task = _task(task_id)
    links = {"task_id": task_id, "task_url": str(task.get_output_log_web_page())}
    model = best_output_model(task)
    if model is not None:
        links.update(model_id=str(model.id), model_url=str(model.url))
    return links


def _checkpoint_from_artifacts(task: Any) -> str | None:
    """Fall back to an uploaded .pt artifact, for tasks that saved one by hand."""
    artifacts: dict[str, Any] = task.artifacts
    preferred = (
        "train_weights_best.pt",
        "train_weights_best",
        "best.pt",
        "best",
        "model",
        "checkpoint",
    )
    named = [name for name in preferred if name in artifacts]
    named.extend(
        name for name in sorted(artifacts) if name not in named and str(name).endswith(".pt")
    )
    for name in named:
        artifact = artifacts[name]
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


def _validated_thresholds(values: dict[str, float]) -> dict[str, float]:
    if not values or any(not name.strip() for name in values):
        raise ValueError("Exact thresholds require nonempty class names")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values.values()):
        raise ValueError("Exact confidence thresholds must be finite values in [0, 1]")
    return values


def _threshold_csv(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["class_name", "confidence"]:
            raise ValueError("Validation threshold CSV requires class_name,confidence columns")
        values: dict[str, float] = {}
        for row in reader:
            name = row["class_name"]
            if name in values:
                raise ValueError(f"Duplicate threshold class {name!r}")
            values[name] = float(row["confidence"])
    return _validated_thresholds(values)


def fetch_best_confidences(task_id: str, split: str) -> dict[str, float]:
    """Prefer exact validation CSV; retain historical per-split payload readers."""
    task = _task(task_id)
    validation = task.artifacts.get(per_split(BEST_CONFIDENCES_PREFIX, "val"))
    if validation is not None:
        local = validation.get_local_copy()
        if local and Path(str(local)).suffix.lower() == ".csv":
            return _threshold_csv(Path(str(local)))
    name = per_split(BEST_CONFIDENCES_PREFIX, split)
    artifact = task.artifacts.get(name)
    if artifact is None:
        raise ValueError(
            f"ClearML task {task_id} ({task.name}) has no {name!r} artifact or exact "
            "validation threshold CSV. Run validation metrics or supply thresholds explicitly."
        )
    payload: Any = artifact.get()
    if isinstance(payload, str):
        payload = json.loads(payload)
    thresholds = _validated_thresholds(_as_threshold_mapping(payload))
    logger.info("Thresholds of task {} for split {!r}: {} classes", task_id, split, len(thresholds))
    return thresholds
