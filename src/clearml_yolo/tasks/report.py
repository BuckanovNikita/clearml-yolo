"""Build developer and business workbooks from one current-test comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_report import report_table
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    upload_artifact,
)
from clearml_yolo.tasks.compare import MANIFEST_NAME, ComparisonManifest


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
) -> ReportResult:
    """Load the paired evaluated dashboards recorded by ``compare``."""
    directory, manifest_path, manifest = _manifest(comparison_dir)
    candidate = _required_path(
        directory, manifest.candidate_dashboard, "candidate dashboard"
    )
    baseline = _required_path(directory, manifest.baseline_dashboard, "baseline dashboard")
    return build_reports(
        candidate,
        baseline,
        output_dir,
        clearml,
        report_config_path,
        split=manifest.split,
        comparison_manifest=manifest_path,
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
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(comparison_manifest) if comparison_manifest is not None else None
    expected = [
        artifact_names.per_split(artifact_names.REPORT_DEV_PREFIX, split),
        artifact_names.per_split(artifact_names.REPORT_BUSINESS_PREFIX, split),
        artifact_names.per_split("report_input_dashboard_candidate", split),
        artifact_names.per_split("report_input_dashboard_baseline", split),
    ]
    if manifest_path is not None:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Comparison manifest does not exist: {manifest_path}")
        expected.append(artifact_names.per_split("report_input_manifest", split))
    if task is not None:
        expect_artifacts(task, expected)
    effective_config_path: str | Path | None = report_config_path
    if report_config_path is not None and task is not None:
        effective_config_path = connect_config_file(
            task, "source_report_configuration", Path(report_config_path)
        )
    config = Config.load(effective_config_path) if effective_config_path else Config.load()

    candidate_reader = MetricsReader(candidate_path)
    baseline_reader = MetricsReader(baseline_path)
    dev_path = destination / f"{artifact_names.REPORT_DEV_PREFIX}_{split}.xlsx"
    business_path = destination / f"{artifact_names.REPORT_BUSINESS_PREFIX}_{split}.xlsx"
    DevReportBuilder(candidate_reader, baseline_reader, config).build(dev_path)
    BusinessReportBuilder(candidate_reader, baseline_reader, config).build(business_path)

    result = ReportResult(
        dev_reports={split: dev_path},
        business_reports={split: business_path},
    )
    logger.info("Split {!r}: {} and {}", split, dev_path.name, business_path.name)
    if task is not None:
        report_table(task, artifact_names.REPORT_SECTION, split, baseline_reader.read())
        upload_artifact(
            task,
            artifact_names.per_split("report_input_dashboard_candidate", split),
            candidate_path,
        )
        upload_artifact(
            task,
            artifact_names.per_split("report_input_dashboard_baseline", split),
            baseline_path,
        )
        if manifest_path is not None:
            upload_artifact(
                task,
                artifact_names.per_split("report_input_manifest", split),
                manifest_path,
            )
        _upload_reports(task, split, dev_path, business_path)
    return result


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
