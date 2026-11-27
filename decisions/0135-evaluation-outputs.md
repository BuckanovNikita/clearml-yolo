# ADR-0135 · Publish split dashboards, audit tables and diagnostics

## Context

A person needs readable summaries, while other tools need complete row evidence and precise numeric values beyond Excel display limits.

## Decision

Write split-specific full and DTRK dashboards, confusion matrix, four confidence-interval plots, evaluation JSON, and a summary workbook. Put thresholds, methodology and row-level match tables in sibling CSVs. Carry [model identity](0154-workbook-identity.md) and [population counts](0151-population-counts.md) where available.

## Consequences

The writer checks all required plot roles and files. Missing diagnostics fail that split. Large row tables and text that Excel cannot represent can still be preserved in CSV. Unavailable scientific values stay unavailable.

## Evidence

- [Diagnostics rendering](../src/clearml_yolo/adapters/reporting/evaluation.py)
- [Workbook and sibling CSV writer](../src/clearml_yolo/adapters/reporting/evaluation_workbook.py)
- [Output and large-table tests](../tests/test_metrics.py)
- [Workbook and JSON formats](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#outputs-per-split)
