# ADR-0150 · Render paired developer and business reports from one comparison

## Context

Users need technical and business views of the same evaluated models. The statistical comparison workbook contains deltas rather than the full metrics of each model.

## Decision

`cy-report` loads the [comparison manifest](0144-comparison-manifest.md), resolves the candidate and baseline dashboards, and delegates rendering to the [report-generator integration](0156-report-generator.md). Apply [eligibility](0152-report-eligibility.md), produce both the [developer workbook](0155-developer-workbook.md) and [business workbook](0153-business-workbook.md), and attach model identities.

## Consequences

A missing manifest or dashboard fails. The report uses the split recorded by the comparison. Optional YAML controls presentation and the training-count cutoff. Both outputs can be traced to the same source pair.

## Evidence

- [Report workflow](../src/clearml_yolo/application/use_cases/report.py)
- [Paired rendering](../src/clearml_yolo/adapters/reporting/reports.py)
- [Input and output cases](../tests/test_report.py)
- [Report command](../docs/commands/cy-report.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#report-workbooks)
