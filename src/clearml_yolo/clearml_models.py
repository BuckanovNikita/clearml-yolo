"""Recover current and historical ClearML checkpoints and frozen thresholds."""

import csv
import gzip
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pandas as pd
from loguru import logger

from clearml_yolo.artifact_names import BEST_CONFIDENCES_VAL
from clearml_yolo.diagnostics import exception_summary, log_exception, redact_text
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
    """Select one output by role, historical filename, then registration order."""
    outputs: list[Any] = list(task.get_models().get("output") or [])
    candidates = [
        model for model in outputs if model.get_metadata("clearml_yolo_checkpoint_role") == "best"
    ]
    if len(candidates) > 1:
        raise ValueError(f"Ambiguous best output models on ClearML task {task.id}")
    if candidates:
        return candidates[0]
    candidates = [
        model for model in outputs if Path(unquote(urlsplit(str(model.url)).path)).name == "best.pt"
    ]
    if len(candidates) > 1:
        raise ValueError(f"Ambiguous best.pt output models on ClearML task {task.id}")
    if candidates:
        return candidates[0]
    if outputs:
        logger.warning(
            "Task {} has no best checkpoint marker; using last registered output model {}",
            task.id,
            outputs[-1].id,
        )
        return outputs[-1]
    return None


_CHECKPOINT_ARTIFACTS = (
    "train_weights_best.pt",
    "train_weights_best",
    "best.pt",
    "best",
    "model",
    "checkpoint",
)


def _select_checkpoint(task: Any) -> tuple[Any, dict[str, str]]:
    """Select once so downloaded weights and provenance always describe one source."""
    links = {"task_id": str(task.id), "task_url": str(task.get_output_log_web_page())}
    model = best_output_model(task)
    if model is not None:
        links.update(model_id=str(model.id), model_url=str(model.url))
        return model, links
    artifacts = task.artifacts
    names = [*_CHECKPOINT_ARTIFACTS, *sorted(name for name in artifacts if name.endswith(".pt"))]
    for name in names:
        if name in artifacts:
            artifact = artifacts[name]
            links["artifact_name"] = name
            # Some legacy SDK artifacts expose no URL; task + artifact name still identifies it.
            artifact_url = getattr(artifact, "url", None)
            if artifact_url:
                links["artifact_url"] = str(artifact_url)
            return artifact, links
    raise ValueError(f"ClearML task {task.id} ({task.name}) has no recoverable checkpoint")


def source_model_links(task_id: str) -> dict[str, str]:
    """Record selected checkpoint provenance without downloading or copying parameters."""
    _, links = _select_checkpoint(_task(task_id))
    return links


def resolve_task_model(task_id: str) -> tuple[Path, dict[str, str]]:
    """Download one selected checkpoint and return its matching source provenance."""
    task = _task(task_id)
    selected, links = _select_checkpoint(task)
    identity = links.get("artifact_name", links.get("model_id", "checkpoint"))
    try:
        checkpoint = selected.get_local_copy()
    except Exception as error:  # noqa: BLE001 - opaque SDK download boundary
        log_exception(
            "Checkpoint download failed",
            error,
            level="DEBUG",
            context={"task_id": task_id, "checkpoint": identity},
        )
        raise ValueError(
            redact_text(f"Cannot download checkpoint {identity!r} on task {task_id}: ")
            + exception_summary(error)
        ) from None
    if not checkpoint:
        raise ValueError(f"Checkpoint {identity!r} on task {task_id} returned no local file")
    path = Path(checkpoint)
    if path.suffix.lower() != ".pt":
        raise ValueError(f"Checkpoint {identity!r} on task {task_id} must be a .pt file: {path}")
    if not path.is_file():
        raise FileNotFoundError(
            f"Checkpoint {identity!r} on task {task_id} returned {path}, but it is not a file"
        )
    logger.info("Checkpoint of task {} ({}): {}", task_id, task.name, path)
    return path, links


def resolve_task_weights(task_id: str) -> Path:
    """Download the selected current or historical checkpoint of a ClearML task."""
    path, _ = resolve_task_model(task_id)
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


_THRESHOLD_ARTIFACTS = (
    BEST_CONFIDENCES_VAL,
    "best_confidences_val",
    "metrics_best_confidences_test",
    "best_confidences_test",
)
_DASHBOARD_ARTIFACTS = (
    "metrics_dashboard_full_val",
    "dashboard_full_val",
    "metrics_dashboard_full_test",
    "dashboard_full_test",
)


def _validated_threshold_pairs(pairs: Sequence[tuple[Any, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for raw_name, raw_value in pairs:
        if raw_name is None or pd.isna(raw_name):
            raise ValueError("Thresholds require nonempty class names")
        name = str(raw_name)
        if not name.strip():
            raise ValueError("Thresholds require nonempty class names")
        if name in values:
            raise ValueError(f"Duplicate threshold class {name!r}")
        if isinstance(raw_value, bool):
            raise TypeError("Confidence thresholds must be numeric values")
        value = float(raw_value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Confidence thresholds must be finite values in [0, 1]")
        values[name] = value
    if not values:
        raise ValueError("Thresholds require nonempty class names")
    return values


def _table_thresholds(frame: pd.DataFrame, *, dashboard: bool) -> dict[str, float]:
    if frame.columns.has_duplicates:
        raise ValueError("Threshold table has duplicate columns")
    if "class_name" in frame.columns:
        frame = frame.set_index("class_name")
    if "confidence" in frame.columns:
        column = "confidence"
    elif not dashboard and len(frame.columns) == 1:
        column = frame.columns[0]
    else:
        raise ValueError("Threshold table requires a confidence column")
    return _validated_threshold_pairs(list(frame[column].items()))


def _threshold_csv(path: Path, *, dashboard: bool = False) -> dict[str, float]:
    # csv preserves string class IDs (including leading zeros) and full float precision.
    with (
        gzip.open(path, "rt", newline="", encoding="utf-8-sig")
        if path.suffix.lower() == ".gz"
        else path.open(newline="", encoding="utf-8-sig")
    ) as stream:
        rows = list(csv.reader(stream))
    required_columns = 2
    if not rows or len(rows[0]) < required_columns:
        raise ValueError("Threshold CSV requires class index and confidence columns")
    header, *data = rows
    if len(header) != len(set(header)):
        raise ValueError("Threshold CSV has duplicate columns")
    class_column = header.index("class_name") if "class_name" in header else 0
    if "confidence" in header:
        confidence_column = header.index("confidence")
    elif not dashboard and len(header) == required_columns:
        confidence_column = 1 - class_column
    else:
        raise ValueError("Threshold CSV requires a confidence column")
    if class_column == confidence_column or any(len(row) != len(header) for row in data):
        raise ValueError("Threshold CSV requires complete class and confidence rows")
    return _validated_threshold_pairs([(row[class_column], row[confidence_column]) for row in data])


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys before a dict could silently replace one threshold."""
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"Duplicate threshold class {name!r}")
        result[name] = value
    return result


def _threshold_payload(payload: Any, *, dashboard: bool) -> dict[str, float]:
    # Historical ClearML serialized some JSON objects as an encoded JSON string.
    for _ in range(2):
        if isinstance(payload, str):
            payload = json.loads(payload, object_pairs_hook=_json_object)
    if isinstance(payload, pd.DataFrame):
        return _table_thresholds(payload, dashboard=dashboard)
    if not dashboard and isinstance(payload, pd.Series):
        return _validated_threshold_pairs(list(payload.items()))
    if not dashboard and isinstance(payload, Mapping):
        return _validated_threshold_pairs(list(payload.items()))
    raise ValueError("Unsupported threshold payload; require class-indexed confidence values")


def _artifact_thresholds(artifact: Any, *, dashboard: bool) -> dict[str, float]:
    local = artifact.get_local_copy()
    if local:
        path = Path(local)
        suffix = path.suffix.lower()
        if suffix == ".csv" or path.name.lower().endswith(".csv.gz"):
            return _threshold_csv(path, dashboard=dashboard)
        if suffix == ".xlsx":
            # Read the class index as strings before pandas can coerce numeric-looking IDs.
            frame = pd.read_excel(path, dtype=str, keep_default_na=False)
            if "class_name" not in frame.columns and len(frame.columns):
                frame = frame.set_index(frame.columns[0])
            return _table_thresholds(frame, dashboard=dashboard)
        if suffix == ".json":
            return _threshold_payload(path.read_text(encoding="utf-8"), dashboard=dashboard)
    return _threshold_payload(artifact.get(), dashboard=dashboard)


def fetch_best_confidences(task_id: str) -> dict[str, float]:
    """Recover frozen thresholds, preferring validation sidecars over legacy dashboards."""
    task = _task(task_id)
    for name in (*_THRESHOLD_ARTIFACTS, *_DASHBOARD_ARTIFACTS):
        if name not in task.artifacts:
            continue
        dashboard = name in _DASHBOARD_ARTIFACTS
        try:
            thresholds = _artifact_thresholds(task.artifacts[name], dashboard=dashboard)
        except Exception as error:  # noqa: BLE001 - report selected SDK/file source
            log_exception(
                "Confidence threshold recovery failed",
                error,
                level="DEBUG",
                context={"task_id": task_id, "artifact": name},
            )
            raise ValueError(
                redact_text(
                    f"Cannot recover confidence thresholds from artifact {name!r} "
                    f"on ClearML task {task_id}: "
                )
                + exception_summary(error)
            ) from None
        if dashboard:
            logger.warning(
                "Recovered thresholds of task {} from legacy dashboard {!r}; "
                "dashboard precision may be rounded and original calibration provenance "
                "is unavailable",
                task_id,
                name,
            )
        logger.info("Thresholds of task {} from {!r}: {} classes", task_id, name, len(thresholds))
        return thresholds
    raise ValueError(
        f"ClearML task {task_id} ({task.name}) has no {BEST_CONFIDENCES_VAL!r} "
        "or supported historical threshold/dashboard artifact. Supply thresholds explicitly."
    )
