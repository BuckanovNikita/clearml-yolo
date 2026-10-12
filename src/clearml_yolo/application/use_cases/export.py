"""Publish an export bundle under one owner without duplicating the trained model."""

from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import ClearMLConfig
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.core.export_requests import ExportRequest, ExportResult, ExportSettings


def export_model(
    export: ExportSettings | dict[str, Any],
    clearml: ClearMLConfig,
    output_dir: str | Path,
    weights: str | Path | None = None,
    ground_truth: str | Path | None = None,
    *,
    deps: WorkflowDependencies,
) -> ExportResult:
    settings = (
        export if isinstance(export, ExportSettings) else ExportSettings.model_validate(export)
    )
    request = ExportRequest(
        **settings.model_dump(),
        weights=Path(weights) if weights is not None else None,
        ground_truth=Path(ground_truth) if ground_truth is not None else None,
    )
    if deps.exporter is None:
        raise ValueError("This dependency bundle does not provide detector export")
    task = deps.tracking.init_task(clearml, stage="export")
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
    result = deps.exporter.execute(request, destination)
    deps.tracking.record_run_configuration(task, {"export_result": result.evidence})
    deps.tracking.expect_artifacts(task, list(result.artifacts))
    for name, artifact in result.artifacts.items():
        deps.tracking.upload_artifact(task, name, artifact)
    if not result.passed:
        raise ValueError("Export verification failed; inspect the retained verification report")
    return result
