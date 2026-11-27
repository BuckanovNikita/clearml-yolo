# ADR-0144 · Bind comparison outputs to named model roles

## Context

Report generation needs the dashboards from one comparison, with the correct role and split, even when multiple runs exist on disk.

## Decision

Write the paired statistical workbook, the exclusions and methodology CSVs, and `comparison_manifest.json`. The manifest binds split, per-role dashboard and prediction filenames, statistical workbook and model identities. [Report generation](0150-report.md) resolves its paired inputs through that manifest.

## Consequences

Readers can distinguish the per-model metric dashboards from the workbook of paired deltas. A missing manifest or missing referenced dashboard prevents report generation. The [candidate-only result](0145-candidate-only.md) does not constitute a paired comparison.

## Evidence

- [Manifest writer](../src/clearml_yolo/application/use_cases/compare.py)
- [Workbook format](../src/clearml_yolo/adapters/reporting/comparison_workbook.py)
- [Manifest consumer](../src/clearml_yolo/application/use_cases/report.py)
- [Manifest and missing-path cases](../tests/test_report.py)
- [Comparison outputs](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#outputs)
