# ADR-0157 · Show readable class aliases without changing scientific keys

## Context

A long opaque identifier can obscure labels in a workbook or plot. Replacing the underlying class key would break subsequent joins and comparisons.

## Decision

Derive readable, distinct display aliases for opaque class values. Apply them to presentation copies. Retain original labels in scientific records and CSVs. The workbook presentation envelope preserves the original workbook underneath the readable labels and can be nested inside the [model identity envelope](0154-workbook-identity.md).

## Consequences

Readers can use a short label on a chart or sheet and still recover the original machine key for another analysis. A visible alias notice identifies transformed workbooks. Two opaque labels must never silently collapse into one class. [Telemetry labels](0324-telemetry-labels.md) govern the related console and scalar presentation.

## Evidence

- [Readable label allocation](../src/clearml_yolo/core/presentation.py)
- [Workbook alias envelope](../src/clearml_yolo/adapters/reporting/workbook_identity.py)
- [Dashboard and plot display](../src/clearml_yolo/adapters/reporting/evaluation.py)
- [Class label round-trip cases](../tests/test_comparison_workbook.py)
- [Workbook identity and aliases](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#readable-plots-and-charts)
