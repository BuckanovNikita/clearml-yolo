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
