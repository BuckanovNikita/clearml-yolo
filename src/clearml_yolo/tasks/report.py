"""Build developer and business workbooks from one current-test comparison."""

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    upload_artifact,
)
from clearml_yolo.filesystem import write_path
from clearml_yolo.model_identity import ModelIdentity, require_model_identity
from clearml_yolo.tasks.compare import MANIFEST_NAME, ComparisonManifest
from clearml_yolo.workbook_identity import (
    annotate_workbook,
    deannotated_workbook,
    workbook_identities,
)


class ReportResult(BaseModel):
    """Generated workbooks keyed by the evaluated split."""

    dev_reports: dict[str, Path] = Field(default_factory=dict)
    business_reports: dict[str, Path] = Field(default_factory=dict)
    skipped_splits: list[str] = Field(default_factory=list)


def _manifest(comparison_dir: str | Path) -> tuple[Path, Path, ComparisonManifest]:
    directory = Path(comparison_dir)
    path = directory / MANIFEST_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"Comparison directory {directory} has no {MANIFEST_NAME}; run cy-compare first"
        )
    return (
        directory,
        path,
        ComparisonManifest.model_validate_json(path.read_text(encoding="utf-8")),
    )


def _required_path(directory: Path, relative: str, description: str) -> Path:
    path = directory / relative
    if not path.is_file():
        raise FileNotFoundError(f"Comparison {description} does not exist: {path}")
    return path


def report(
    comparison_dir: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    report_config_path: str | Path | None = None,
    baseline_label: str | None = None,
    candidate_label: str | None = None,
) -> ReportResult:
    """Load the paired evaluated dashboards recorded by ``compare``."""
    directory, manifest_path, manifest = _manifest(comparison_dir)
    candidate = _required_path(directory, manifest.candidate_dashboard, "candidate dashboard")
    baseline = _required_path(directory, manifest.baseline_dashboard, "baseline dashboard")
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
) -> ReportResult:
    """Render both established workbook formats from the same evaluated pair."""
    from report_generator.config import Config
    from report_generator.core.reader import MetricsReader
    from report_generator.reports.business.builder import BusinessReportBuilder
    from report_generator.reports.dev.builder import DevReportBuilder

    candidate_path = Path(candidate_dashboard)
    baseline_path = Path(baseline_dashboard)
    for path, description in (
        (candidate_path, "candidate dashboard"),
        (baseline_path, "baseline dashboard"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Comparison {description} does not exist: {path}")

    task = init_task(clearml, stage="report")
    destination = write_path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(comparison_manifest) if comparison_manifest is not None else None
    expected = [
        artifact_names.per_split(artifact_names.REPORT_DEV_PREFIX, split),
        artifact_names.per_split(artifact_names.REPORT_BUSINESS_PREFIX, split),
    ]
    if manifest_path is not None and not manifest_path.is_file():
        raise FileNotFoundError(f"Comparison manifest does not exist: {manifest_path}")
    if task is not None:
        expect_artifacts(task, expected)
    effective_config_path: str | Path | None = report_config_path
    if report_config_path is not None and task is not None:
        effective_config_path = connect_config_file(task, "report", Path(report_config_path))
    config = Config.load(effective_config_path) if effective_config_path else Config.load()

    identities = {
        "baseline": _report_identity(baseline_path, "baseline", baseline_identity, baseline_label),
        "candidate": _report_identity(
            candidate_path, "candidate", candidate_identity, candidate_label,
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
    with (
        deannotated_workbook(candidate_path) as candidate_source,
        deannotated_workbook(baseline_path) as baseline_source,
    ):
        candidate_reader = MetricsReader(candidate_source)
        baseline_reader = MetricsReader(baseline_source)
        DevReportBuilder(candidate_reader, baseline_reader, config).build(dev_path)
        BusinessReportBuilder(candidate_reader, baseline_reader, config).build(business_path)
    annotate_workbook(dev_path, identities)
    annotate_workbook(business_path, identities)

    result = ReportResult(
        dev_reports={split: dev_path},
        business_reports={split: business_path},
    )
    logger.info("Split {!r}: {} and {}", split, dev_path.name, business_path.name)
    if task is not None:
        _upload_reports(task, split, dev_path, business_path)
    return result


def _report_identity(
    path: Path, role: str, supplied: ModelIdentity | None, label: str | None,
) -> ModelIdentity:
    stored = workbook_identities(path)
    identity = stored.get(role) or stored.get("model")
    if identity is not None and supplied is not None and identity != supplied:
        raise ValueError(f"{role} dashboard identity does not match comparison manifest")
    return require_model_identity(identity or supplied, label)


def _upload_reports(task: Any, split: str, dev_path: Path, business_path: Path) -> None:
    upload_artifact(
        task,
        artifact_names.per_split(artifact_names.REPORT_DEV_PREFIX, split),
        dev_path,
    )
    upload_artifact(
        task,
        artifact_names.per_split(artifact_names.REPORT_BUSINESS_PREFIX, split),
        business_path,
    )
