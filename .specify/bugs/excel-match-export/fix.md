# Bug Fix: Excel match-table export

- **Slug**: excel-match-export (reused from assessment context)
- **Fixed**: 2026-10-01
- **Assessment**: [Assessment](assessment.md)
- **Status**: applied; local verification and documentation stage complete (production verification partial)

## Summary

Excel now contains dashboard/metric tables only. Adjacent CSV files retain the
row-level matches, standalone thresholds, methodology and excluded classes.
Each sidecar is published through the existing strict ClearML table adapter;
content deduplication and failure barriers remain active.

## Changes

| File | Change |
|---|---|
| `src/clearml_yolo/tasks/metrics.py` | XLSX summary, per-class and confusion matrix; CSV match/threshold/methodology sidecars; publish all sidecars |
| `src/clearml_yolo/comparison/workbook.py` | XLSX comparison metrics only; CSV exclusions and methodology; return sidecar paths |
| `src/clearml_yolo/tasks/compare.py` | Publish paired comparison sidecars; skipped candidate XLSX Classes/Summary with CSV thresholds/methodology |
| `tests/test_metrics.py` | CSV round-trip regression for Excel-illegal characters; empty tables and exact inventory |
| `tests/test_comparison_workbook.py` | CSV round-trips/headers and preserved Excel comparison presentation |
| `tests/test_comparison_assemble.py` | Paired and skipped comparison publication inventories |

## Local verification

Before implementation, focused tests reported 9 failures and 21 passes: the new
regression raised IllegalCharacterError at prediction_matches.to_excel and the
remaining failures showed the requested CSV layout was absent.
After implementation, the affected metrics/workbook/assembly tests reported
69 passes. Scoped Ruff, mypy and import-linter passed. Full-suite verification
and documentation validation will be recorded in [verification](test.md).

## Documentation update stage

Scope and ownership follow the assessment. An independent documentation agent
updates README, publication contract, active spec, quickstart, migration, contract
index and integration guidance while parent verifies code. Final changed paths and
validation outcomes are recorded in test.md; the documentation stage is complete.

## Deviations from assessment

No functional deviations. The assessment was recorded after implementation began
because the automatic Spec Kit instructions arrived during this work. No source,
checkout or reference in the external dependencies was changed by this task.
Pre-existing concurrent filesystem/configuration edits remain intact.

## Follow-ups and limitations

The production exception type/data and real ClearML uploads are unavailable.
A synthetic reproduction verifies the reported serializer path, not production.
Removed XLSX sheets require sidecar-aware consumers; migration guidance is in scope.
No commit was requested or performed.
