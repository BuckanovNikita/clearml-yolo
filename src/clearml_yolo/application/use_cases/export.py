"""Publish an export bundle under one owner without duplicating the trained model."""

from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import ClearMLConfig, GroundTruthInput
from clearml_yolo.application.ground_truth import normalize_ground_truth, resolve_ground_truth
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.core.export_requests import ExportRequest, ExportResult, ExportSettings


def _validate_inputs(
    settings: ExportSettings,
    weights: str | Path | None,
    ground_truth: GroundTruthInput | None,
) -> GroundTruthInput | None:
    settings.validate_input_presence(
        has_weights=weights is not None, has_ground_truth=ground_truth is not None
    )
    return normalize_ground_truth(ground_truth) if ground_truth is not None else None


def export_model(
    export: ExportSettings | dict[str, Any],
    clearml: ClearMLConfig,
    output_dir: str | Path,
    weights: str | Path | None = None,
    ground_truth: GroundTruthInput | None = None,
    *,
    deps: WorkflowDependencies,
) -> ExportResult:
    settings = (
        export if isinstance(export, ExportSettings) else ExportSettings.model_validate(export)
    )
    ground_truth = _validate_inputs(settings, weights, ground_truth)
    if deps.exporter is None:
        raise ValueError("This dependency bundle does not provide detector export")
    task = deps.tracking.init_task(clearml, stage="export")
    resolved_truth = (
        resolve_ground_truth(ground_truth, task=task, deps=deps)
        if ground_truth is not None else None
    )
    request = ExportRequest(
        **settings.model_dump(),
        weights=Path(weights) if weights is not None else None,
        ground_truth=resolved_truth.path if resolved_truth is not None else None,
    )
    destination = deps.storage.write_path(output_dir)
    deps.storage.mkdir(destination, parents=True, exist_ok=True)
    if weights is not None:
        checkpoint, identity = deps.repository.resolve_weights_with_identity(weights)
        request = request.model_copy(update={"weights": Path(checkpoint)})
        deps.tracking.record_run_configuration(
            task,
            {
                "source_model": identity.model_dump(mode="json")
                if identity is not None
                else {
                    "checkpoint_sha256": deps.tracking.file_digest(Path(checkpoint)),
                },
            },
        )
    published: dict[str, Path] = {}

    def artifact_ready(name: str, path: Path) -> None:
        if name in published:
            raise ValueError(f"Export artifact {name!r} was already published")
        deps.tracking.expect_artifacts(task, [name])
        deps.tracking.upload_artifact(task, name, path)
        published[name] = path

    result = deps.exporter.execute(request, destination, artifact_ready=artifact_ready)
    for name, path in published.items():
        if result.artifacts.get(name) != path:
            raise ValueError(f"Export result disagrees with published artifact {name!r}")
    for name, path in result.artifacts.items():
        if name not in published:
            artifact_ready(name, path)
    deps.tracking.record_run_configuration(task, {"export_result": result.evidence})
    if not result.passed:
        raise ValueError("Export verification failed; inspect the retained verification report")
    return result
