# ADR-0155 · Show metric availability in the developer report

## Context

The same metric can be available for one model and unavailable for another. A reviewer needs to know both the value and the class population entering each comparison.

## Decision

Render the developer view from the per-model dashboards with availability counts below its tables. Apply the [eligibility rule](0152-report-eligibility.md), preserve available one-sided metrics and record the compared model roles with the [identity footer](0154-workbook-identity.md).

## Consequences

The developer workbook exposes the classes contributing to an aggregate and classes excluded from it. A missing operand leaves a paired difference unavailable. Readers can inspect the original dashboard values through the [report workflow](0150-report.md).

## Evidence

- [DevReportBuilder presentation configuration](../src/clearml_yolo/adapters/reporting/reports.py)
- [Real developer builder and availability cases](../tests/test_report_class_availability.py)
- [Developer workbook](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#report-workbooks)
