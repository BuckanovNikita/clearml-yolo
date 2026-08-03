"""Compare the new model against a baseline and publish the comparison workbooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.tasks.metrics import DASHBOARD_PREFIX

BaselineSource = Literal["clearml", "local", "none"]


class BaselineConfig(BaseModel):
    """Where the previous model's dashboards come from."""

    source: BaselineSource = "clearml"
    project_name: str | None = None
    task_id: str | None = None
    task_name: str | None = None
    directory: Path | None = None
    artifact_prefix: str = "dashboard_full"


class ReportResult(BaseModel):
    """Generated workbooks, keyed by split."""

    dev_reports: dict[str, Path] = Field(default_factory=dict)
    business_reports: dict[str, Path] = Field(default_factory=dict)
    skipped_splits: list[str] = Field(default_factory=list)


def _latest_baseline_task(config: BaselineConfig, fallback_project: str) -> Any | None:
    from clearml import Task

    if config.task_id:
        return Task.get_task(task_id=config.task_id)

    project = config.project_name or fallback_project
    tasks: list[Any] = Task.get_tasks(
        project_name=project,
        task_name=config.task_name,
        task_filter={"status": ["completed", "published"], "order_by": ["-last_update"]},
    )
    if not tasks:
        logger.warning("No completed ClearML task found in project {!r}", project)
        return None
    logger.info("Baseline task: {} ({})", tasks[0].id, tasks[0].name)
    return tasks[0]


def _baseline_from_clearml(
    config: BaselineConfig, splits: list[str], fallback_project: str, workdir: Path
) -> dict[str, Path]:
    task = _latest_baseline_task(config, fallback_project)
    if task is None:
        return {}

    import pandas as pd

    resolved: dict[str, Path] = {}
    for split in splits:
        artifact = task.artifacts.get(f"{config.artifact_prefix}_{split}")
        if artifact is None:
            logger.warning("Baseline task {} has no artifact for split {!r}", task.id, split)
            continue
        # The artifact is a CSV; report-generator only reads .xlsx, so convert it.
        frame = pd.read_csv(artifact.get_local_copy(), index_col=0)
        destination = workdir / f"baseline_{split}.xlsx"
        frame.to_excel(destination)
        resolved[split] = destination
        logger.info("Baseline for split {!r}: {}", split, destination)
    return resolved


def _baseline_from_local(config: BaselineConfig, splits: list[str]) -> dict[str, Path]:
    if config.directory is None:
        raise ValueError("report.baseline.source='local' requires baseline.directory")

    resolved: dict[str, Path] = {}
    for split in splits:
        candidate = config.directory / f"{DASHBOARD_PREFIX}_{split}.xlsx"
        if candidate.is_file():
            resolved[split] = candidate
        else:
            logger.warning("No baseline workbook at {}", candidate)
    return resolved


def discover_dashboards(metrics_dir: str | Path, splits: list[str]) -> dict[str, Path]:
    """Find the dashboard workbook digital-metrics wrote for each split."""
    directory = Path(metrics_dir)
    found: dict[str, Path] = {}
    for split in splits:
        candidate = directory / f"{DASHBOARD_PREFIX}_{split}.xlsx"
        if candidate.is_file():
            found[split] = candidate
        else:
            logger.warning("No dashboard for split {!r} at {}", split, candidate)
    return found


def report(
    metrics_dir: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    baseline: BaselineConfig,
    splits: list[str] | None = None,
    report_config_path: str | Path | None = None,
) -> ReportResult:
    """Standalone entrypoint: locate dashboards on disk, then compare them."""
    splits = splits or ["train", "val", "test"]
    dashboards = discover_dashboards(metrics_dir, splits)
    if not dashboards:
        raise FileNotFoundError(
            f"No dashboard workbooks found in {metrics_dir} for splits {splits}. "
            "Run the metrics stage first."
        )
    return build_reports(dashboards, output_dir, clearml, baseline, report_config_path)


def build_reports(
    dashboards: dict[str, Path],
    output_dir: str | Path,
    clearml: ClearMLConfig,
    baseline: BaselineConfig,
    report_config_path: str | Path | None = None,
) -> ReportResult:
    """Produce dev and business comparison workbooks for every split with a baseline.

    Comparison is always new minus previous, so argument order into the builders is
    load-bearing.
    """
    from report_generator.config import Config
    from report_generator.core.reader import MetricsReader
    from report_generator.reports.business.builder import BusinessReportBuilder
    from report_generator.reports.dev.builder import DevReportBuilder

    task = init_task(clearml, stage="report")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    splits = list(dashboards)
    result = ReportResult()

    if baseline.source == "none":
        logger.info("Baseline disabled; publishing new metrics without comparison")
        result.skipped_splits = splits
        return result

    if baseline.source == "clearml":
        baselines = _baseline_from_clearml(baseline, splits, clearml.project_name, destination)
    else:
        baselines = _baseline_from_local(baseline, splits)

    if not baselines:
        logger.warning("No baseline dashboards resolved; nothing to compare against")
        result.skipped_splits = splits
        return result

    config = Config.load(report_config_path) if report_config_path else Config.load()

    for split, new_dashboard in dashboards.items():
        previous = baselines.get(split)
        if previous is None:
            logger.warning("Skipping split {!r}: no baseline dashboard", split)
            result.skipped_splits.append(split)
            continue

        dev_path = destination / f"report_dev_{split}.xlsx"
        business_path = destination / f"report_business_{split}.xlsx"

        DevReportBuilder(MetricsReader(new_dashboard), MetricsReader(previous), config).build(
            dev_path
        )
        BusinessReportBuilder(MetricsReader(new_dashboard), MetricsReader(previous), config).build(
            business_path
        )

        result.dev_reports[split] = dev_path
        result.business_reports[split] = business_path
        logger.info("Split {!r}: {} and {}", split, dev_path.name, business_path.name)

        if task is not None:
            task.upload_artifact(name=f"report_dev_{split}", artifact_object=dev_path)
            task.upload_artifact(name=f"report_business_{split}", artifact_object=business_path)

    return result
