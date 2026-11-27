# ADR-0145 · Retain candidate diagnostics when no automatic baseline exists

## Context

A project may have no completed production baseline on its first comparison. Its candidate can still be evaluated on the requested split.

## Decision

Allow absence only when resolving the automatic baseline. Score the candidate with its own thresholds and publish a skipped comparison status and candidate-only evaluation workbook, thresholds and methodology.

## Consequences

The candidate gets per-model diagnostics. With no paired comparison manifest from this path, these results alone cannot feed `cy-report`. An absent explicitly requested baseline fails instead of silently changing the analysis.

## Evidence

- [Automatic-absence branch](../src/clearml_yolo/application/use_cases/compare.py)
- [Candidate workbook writer](../src/clearml_yolo/adapters/reporting/evaluation_workbook.py)
- [Explicit and automatic absence cases](../tests/test_comparison_assemble.py)
- [Candidate-only files](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#missing-automatic-baseline)
