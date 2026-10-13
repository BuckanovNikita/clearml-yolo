"""Concrete workflow operations behind application ports."""

from pathlib import Path

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.reporting.workbook_identity import (
    deannotated_workbook,
)
from clearml_yolo.adapters.storage.filesystem import write_path


@trace_operation("report.build")
def build_reports(
    candidate: Path,
    baseline: Path,
    dev_path: Path,
    business_path: Path,
    config_path: str | Path | None,
) -> None:
    dev_path = write_path(dev_path)
    business_path = write_path(business_path)
    with trace_operation("report.backend.import"):
        from report_generator.config import Config
        from report_generator.v2 import (
            BusinessReportBuilder,
            DevReportBuilder,
            PresentationOptions,
            read_metrics_table,
        )

    with trace_operation("report.config.load"):
        config = Config.load(config_path) if config_path else Config.load()
    with (
        deannotated_workbook(candidate) as candidate_source,
        deannotated_workbook(baseline) as baseline_source,
    ):
        with trace_operation("report.workbooks.read"):
            candidate_reader = read_metrics_table(candidate_source)
            baseline_reader = read_metrics_table(baseline_source)
        with trace_operation("report.developer.build", context={"path": str(dev_path)}):
            DevReportBuilder(
                candidate_reader,
                baseline_reader,
                config,
                presentation=PresentationOptions(counts="below_table"),
            ).build(dev_path)
        with trace_operation("report.business.build", context={"path": str(business_path)}):
            BusinessReportBuilder(
                candidate_reader,
                baseline_reader,
                config,
                presentation=PresentationOptions(counts="below_table"),
            ).build(business_path)
