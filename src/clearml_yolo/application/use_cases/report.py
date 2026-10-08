"""Build developer and business workbooks from one current-test comparison."""

__all__ = ["ReportResult"]
from pathlib import Path

from clearml_yolo.application.contracts import ClearMLConfig, ComparisonManifest, ReportResult
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies
from clearml_yolo.application.use_cases.compare import MANIFEST_NAME
from clearml_yolo.core import artifact_names
from clearml_yolo.core.identity import ModelIdentity, require_model_identity


def _manifest(
    comparison_dir: str | Path, *, deps: WorkflowDependencies
) -> tuple[Path, Path, ComparisonManifest]:
    directory = Path(comparison_dir)
    path = directory / MANIFEST_NAME
    if not deps.storage.is_file(path):
        raise FileNotFoundError(
            f"Comparison directory {directory} has no {MANIFEST_NAME}; run cy-compare first"
        )
    return (
        directory,
        path,
        ComparisonManifest.model_validate_json(deps.storage.read_text(path, encoding="utf-8")),
    )


def _required_path(
    directory: Path, relative: str, description: str, *, deps: WorkflowDependencies
) -> Path:
    path = directory / relative
    if not deps.storage.is_file(path):
        raise FileNotFoundError(f"Comparison {description} does not exist: {path}")
    return path


def report(
    comparison_dir: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    report_config_path: str | Path | None = None,
    baseline_label: str | None = None,
    candidate_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> ReportResult:
    """Load the paired evaluated dashboards recorded by ``compare``."""
    directory, manifest_path, manifest = _manifest(comparison_dir, deps=deps)
    candidate = _required_path(
        directory, manifest.candidate_dashboard, "candidate dashboard", deps=deps
    )
    baseline = _required_path(
        directory, manifest.baseline_dashboard, "baseline dashboard", deps=deps
    )
    return build_reports(
        candidate,
        baseline,
        output_dir,
        clearml,
        report_config_path,
        split=manifest.split,
        comparison_manifest=manifest_path,
        baseline_identity=manifest.baseline_identity,
        candidate_identity=manifest.candidate_identity,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
        deps=deps,
    )


def build_reports(
    candidate_dashboard: str | Path,
    baseline_dashboard: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    report_config_path: str | Path | None = None,
    *,
    split: str = "test",
    comparison_manifest: str | Path | None = None,
    baseline_identity: ModelIdentity | None = None,
    candidate_identity: ModelIdentity | None = None,
    baseline_label: str | None = None,
    candidate_label: str | None = None,
    deps: WorkflowDependencies,
) -> ReportResult:
    """Render both established workbook formats from the same evaluated pair."""
    candidate_path = Path(candidate_dashboard)
    baseline_path = Path(baseline_dashboard)
    for path, description in (
        (candidate_path, "candidate dashboard"),
        (baseline_path, "baseline dashboard"),
    ):
        if not deps.storage.is_file(path):
            raise FileNotFoundError(f"Comparison {description} does not exist: {path}")
    task = deps.tracking.init_task(clearml, stage="report")
    destination = deps.storage.write_path(output_dir)
    deps.storage.mkdir(destination, parents=True, exist_ok=True)
    manifest_path = Path(comparison_manifest) if comparison_manifest is not None else None
    expected = [
        artifact_names.per_split(artifact_names.REPORT_DEV_PREFIX, split),
        artifact_names.per_split(artifact_names.REPORT_BUSINESS_PREFIX, split),
    ]
    if manifest_path is not None and (not deps.storage.is_file(manifest_path)):
        raise FileNotFoundError(f"Comparison manifest does not exist: {manifest_path}")
    if task is not None:
        deps.tracking.expect_artifacts(task, expected)
    effective_config_path: str | Path | None = report_config_path
    if report_config_path is not None and task is not None:
        effective_config_path = deps.tracking.connect_config_file(
            task, "report", Path(report_config_path)
        )
    identities = {
        "baseline": _report_identity(
            baseline_path, "baseline", baseline_identity, baseline_label, deps=deps
        ),
        "candidate": _report_identity(
            candidate_path, "candidate", candidate_identity, candidate_label, deps=deps
        ),
    }
    dev_path = (
        destination
        / f"{artifact_names.REPORT_DEV_PREFIX}_{artifact_names.split_component(split)}.xlsx"
    )
    business_path = (
        destination
        / f"{artifact_names.REPORT_BUSINESS_PREFIX}_{artifact_names.split_component(split)}.xlsx"
    )
    deps.renderer.build_reports(
        candidate_path, baseline_path, dev_path, business_path, effective_config_path
    )
    deps.renderer.annotate_workbook(dev_path, identities)
    deps.renderer.annotate_workbook(business_path, identities)
    result = ReportResult(dev_reports={split: dev_path}, business_reports={split: business_path})
    deps.resources.log("INFO", "Split {!r}: {} and {}", split, dev_path.name, business_path.name)
    if task is not None:
        _upload_reports(task, split, dev_path, business_path, deps=deps)
    return result


def _report_identity(
    path: Path,
    role: str,
    supplied: ModelIdentity | None,
    label: str | None,
    *,
    deps: WorkflowDependencies,
) -> ModelIdentity:
    stored = deps.renderer.workbook_identities(path)
    identity = stored.get(role) or stored.get("model")
    if identity is not None and supplied is not None and (identity != supplied):
        raise ValueError(f"{role} dashboard identity does not match comparison manifest")
    return require_model_identity(identity or supplied, label)


def _upload_reports(
    task: TaskHandle | None,
    split: str,
    dev_path: Path,
    business_path: Path,
    *,
    deps: WorkflowDependencies,
) -> None:
    deps.tracking.upload_artifact(
        task, artifact_names.per_split(artifact_names.REPORT_DEV_PREFIX, split), dev_path
    )
    deps.tracking.upload_artifact(
        task, artifact_names.per_split(artifact_names.REPORT_BUSINESS_PREFIX, split), business_path
    )
