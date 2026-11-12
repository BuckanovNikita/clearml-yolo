"""Recover model-owned prepared populations published since CY 0.25.0."""

from pathlib import Path

from clearml_yolo.adapters.clearml import models
from clearml_yolo.adapters.observability.diagnostics import log_exception
from clearml_yolo.adapters.storage.population import population_counts
from clearml_yolo.core.artifact_names import GROUND_TRUTH
from clearml_yolo.core.identity import ModelIdentity


def recover_population_counts(identity: ModelIdentity) -> dict[str, dict[str, int]] | None:
    """Read original task truth only after verifying its checkpoint association."""
    if identity.training_task_id is None or identity.checkpoint_sha256 is None:
        return None
    try:
        counts = _recover(identity)
    except Exception as error:  # noqa: BLE001 - opaque SDK and historical artifact boundary
        log_exception(
            "Original dataset counts unavailable",
            error,
            level="WARNING",
            context={"training_task_id": identity.training_task_id},
        )
        return None
    else:
        return counts


def _recover(identity: ModelIdentity) -> dict[str, dict[str, int]]:
    if identity.training_task_id is None:
        raise ValueError("Training task identity is required")
    _, links = models.resolve_task_model(identity.training_task_id)
    expected = identity.model_dump(include={"training_task_id", "checkpoint_sha256", "model_id"}, exclude_none=True)
    if any(links.get(key) != value for key, value in expected.items()):
        raise ValueError("Original training task does not own the selected checkpoint identity")
    task = models._task(identity.training_task_id)  # noqa: SLF001 - shared SDK task lookup boundary
    artifact = task.artifacts.get(GROUND_TRUTH)
    if artifact is None:
        raise ValueError("Original training task has no prepared ground-truth artifact")
    local = artifact.get_local_copy()
    if not local:
        raise ValueError("Original training population returned no local file")
    counts = population_counts(Path(local))
    if counts is None:
        raise ValueError("Original training population lacks split/class evidence")
    return counts
