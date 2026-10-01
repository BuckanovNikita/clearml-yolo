# Bug Assessment: Excel match-table export

- **Slug**: excel-match-export
- **Created**: 2026-10-01
- **Source**: pasted traceback fragment and requested export policy
- **Verdict**: valid (export limitation reproduced; original exception unspecified)
- **Severity**: medium — metrics completion can fail while serializing row-level evidence.

## Report

The supplied traceback ends at `_write_evaluation_workbook` calling
`evaluated.pred_matches.to_excel(writer, sheet_name="prediction_matches", index=False)`.
The exception type/message and production input are unavailable. The user directs:
“Store only dashboards and metric tables in excel all other in csv.”

## Symptom and reproduction

The previous exporter embedded match tables, thresholds and methodology in Excel.
A synthetic predictions CSV with a diagnostic string containing U+0001 reaches the
reported call and raises `openpyxl.utils.exceptions.IllegalCharacterError`.
`tests/test_metrics.py::test_match_tables_preserve_excel_illegal_characters_in_csv`
reproduces that limitation before the fix. This is a controlled example, not a
confirmed diagnosis of the user's exception. Excel row limits are another format
constraint; the user's original row count is unknown.

## Suspected code paths and root cause

- `src/clearml_yolo/tasks/metrics.py::_write_evaluation_workbook` writes arbitrary
  row-level evidence through Excel, exposing it to Excel restrictions.
- `src/clearml_yolo/comparison/workbook.py::write_comparison_workbook` embeds
  exclusions and methodology in its metric workbook.
- `src/clearml_yolo/tasks/compare.py::_skip_without_baseline` embeds standalone
  thresholds and methodology in its candidate metric workbook.

Confidence is high for the reproduced serialization limitation, and unknown for
the exact production exception. No change to digital-metrics is required.

## Preferred remediation

Keep dashboards, summary/per-class metrics, confusion matrices and statistical
comparison metric tables in XLSX. Move match tables, standalone threshold tables,
methodology and exclusions to adjacent CSV files. Preserve full numeric precision,
empty-table headers, local diagnostics and ClearML table publication/deduplication.
Keep structured evaluation JSON, manifests, configs and plots in their existing
non-tabular formats. Report/dashboard consumers keep their metric XLSX paths.

## Scope, tests and documentation

Source ownership: the three files above. Tests: `tests/test_metrics.py`,
`tests/test_comparison_workbook.py`, `tests/test_comparison_assemble.py`.
Test CSV round-trips, illegal-character retention, empty predictions/exclusions,
Excel-only metric sheets, publication inventories and skipped comparison.

Documentation review scope: README; current contract index; feature 008 publication
contract, active spec and quickstart; export migration; project integration skill
and relevant references. Update and validate these before completion. No native
configuration, environment endpoint, dependency, submodule or lock change is needed.

## Risks and open questions

Consumers of removed workbook sheets must switch to CSV sidecars. Sidecars remain
required publication inputs; table-content deduplication may reuse existing artifact
aliases. Original production data/exception and live ClearML uploads are unverified.
The requested format policy supplies enough direction to implement independently.

## Workflow timing

Spec Kit completion instructions arrived after code implementation and focused tests
had begun. This assessment records the already investigated evidence without
rewriting that sequence or claiming a production reproduction.
