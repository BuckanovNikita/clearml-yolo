"""Concrete workflow operations behind application ports."""

from pathlib import Path

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.reporting.report_layout import compact_report_counts
from clearml_yolo.adapters.reporting.workbook_identity import (
    deannotated_workbook,
)


@trace_operation("report.build")
def build_reports(
    candidate: Path,
    baseline: Path,
    dev_path: Path,
    business_path: Path,
    config_path: str | Path | None,
) -> None:
    with trace_operation("report.backend.import"):
        from report_generator.config import Config
        from report_generator.core.reader import MetricsReader
        from report_generator.reports.business.builder import BusinessReportBuilder
        from report_generator.reports.dev.builder import DevReportBuilder

    with trace_operation("report.config.load"):
        config = Config.load(config_path) if config_path else Config.load()
    with (
        deannotated_workbook(candidate) as candidate_source,
        deannotated_workbook(baseline) as baseline_source,
    ):
        with trace_operation("report.workbooks.read"):
            candidate_reader = MetricsReader(candidate_source)
            baseline_reader = MetricsReader(baseline_source)
        with trace_operation("report.developer.build", context={"path": str(dev_path)}):
            DevReportBuilder(candidate_reader, baseline_reader, config).build(dev_path)
        with trace_operation("report.business.build", context={"path": str(business_path)}):
            BusinessReportBuilder(candidate_reader, baseline_reader, config).build(business_path)
    sheets = (config.sheet_names.model1, config.sheet_names.model2, config.sheet_names.comparison)
    with trace_operation("report.class_counts.compact"):
        compact_report_counts(dev_path, sheets)
        compact_report_counts(
            business_path, sheets, translations=config.business.column_translations
        )
