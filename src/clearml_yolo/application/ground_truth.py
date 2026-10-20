"""Ground-truth selection policy shared by standalone and composed workflows."""

from collections.abc import Mapping
from pathlib import Path

from clearml_yolo.application.contracts import (
    ClearMLDatasetRef,
    GroundTruthInput,
    ResolvedGroundTruth,
)
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies


def normalize_ground_truth(
    source: GroundTruthInput,
) -> Path | ClearMLDatasetRef | ResolvedGroundTruth:
    """Validate source shape without touching files, SDKs or tracking."""
    if isinstance(source, ResolvedGroundTruth | ClearMLDatasetRef):
        return source
    if isinstance(source, Mapping):
        return ClearMLDatasetRef.model_validate(dict(source))
    if isinstance(source, str | Path):
        if not str(source).strip():
            raise ValueError("Ground truth path must not be empty")
        return Path(source)
    raise ValueError("ground_truth must be a CSV path or a ClearML dataset reference")


def resolve_ground_truth(
    source: GroundTruthInput, *, task: TaskHandle | None, deps: WorkflowDependencies
) -> ResolvedGroundTruth:
    """Resolve the original input once; nested workflows receive the resolved record."""
    normalized = normalize_ground_truth(source)
    if isinstance(normalized, ResolvedGroundTruth):
        return normalized
    if isinstance(normalized, Path):
        deps.resources.log(
            "WARNING",
            "Using local ground-truth CSV {}; prefer a ClearML dataset reference "
            "for versioned annotations.",
            normalized,
        )
        return ResolvedGroundTruth(path=normalized)
    if deps.ground_truth_repository is None:
        raise ValueError("This dependency bundle does not provide ClearML ground-truth resolution")
    resolved = deps.ground_truth_repository.resolve(normalized)
    if task is not None:
        deps.tracking.record_run_configuration(
            task,
            {
                "ground_truth_source": {
                    "requested": normalized.model_dump(exclude_none=True),
                    "dataset_id": resolved.dataset_id,
                    "project_name": resolved.project_name,
                    "name": resolved.name,
                    "version": resolved.version,
                    "csv_sha256": resolved.csv_sha256,
                }
            },
        )
    return resolved
