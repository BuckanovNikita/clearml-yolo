"""Recover current best Output Models and exact validation thresholds from ClearML."""

import csv
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from loguru import logger

from clearml_yolo.artifact_names import BEST_CONFIDENCES_VAL
from clearml_yolo.filesystem import model_weights_path

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
    """Group a user regex and require the entire task name to match."""
    if not task_name:
        return None
    # PCRE accepts a final newline before \Z; the assertion makes the end strict
    # in both MongoDB and Python regex engines.
    return rf"\A(?:{task_name})\Z(?![\s\S])"


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
    return a different one. Anchoring also supports deliberate patterns such as
    ``yolo-v1.*``.
    """
    from clearml import Task

    tasks: list[Any] = Task.get_tasks(
        project_name=project_name,
        task_name=_anchored(task_name),
        tags=(["__$all", *tags] if len(tags) > 1 else list(tags)) if tags else None,
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
        model for model in outputs if model.get_metadata("clearml_yolo_checkpoint_role") == "best"
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


def resolve_task_weights(task_id: str) -> Path:
    """Download the best Output Model a ClearML task produced."""
    task = _task(task_id)
    checkpoint = _checkpoint_from_models(task)
    if checkpoint is None:
        raise ValueError(
            f"ClearML task {task_id} ({task.name}) registered no best Output Model, so it "
            "carries no current checkpoint to run. Point at the training task or pass a local "
            "path instead."
        )
    path = Path(checkpoint)
    if not path.is_file():
        raise FileNotFoundError(f"ClearML returned {path} for task {task_id}, but it is not a file")
    logger.info("Checkpoint of task {} ({}): {}", task_id, task.name, path)
    return path


def resolve_weights(weights: str | Path) -> str | Path:
    """Accept either a checkpoint on disk or a ClearML task id, and return a real file."""
    if isinstance(weights, str) and "://" in weights:
        return weights
    candidate = Path(weights)
    if candidate.exists():
        return candidate
    text = str(weights)
    if looks_like_task_id(text):
        return resolve_task_weights(text)
    # Native downloads use the workspace, while existing and explicit file paths stay intact.
    return model_weights_path(weights)


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


def fetch_best_confidences(task_id: str) -> dict[str, float]:
    """Read exact validation thresholds from the current CSV publication."""
    task = _task(task_id)
    artifact = task.artifacts.get(BEST_CONFIDENCES_VAL)
    if artifact is None:
        raise ValueError(
            f"ClearML task {task_id} ({task.name}) has no {BEST_CONFIDENCES_VAL!r} CSV "
            "artifact. Run validation metrics or supply thresholds explicitly."
        )
    local = artifact.get_local_copy()
    path = Path(str(local))
    if not local or path.suffix.lower() != ".csv":
        raise ValueError(f"ClearML artifact {BEST_CONFIDENCES_VAL!r} must be a CSV file")
    thresholds = _threshold_csv(path)
    logger.info("Validation thresholds of task {}: {} classes", task_id, len(thresholds))
    return thresholds
