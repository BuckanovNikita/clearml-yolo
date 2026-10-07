# Implementation Plan: Model report identity

**Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved user plan using existing finalized model naming, a shared
identity value, durable checkpoint/prediction metadata, evaluation contexts, and
comparison manifests. Add project-owned workbook annotations and reading adapters.

## Technical Context

Python 3.12, Pydantic, Hydra, ClearML, pandas, openpyxl, standard-library OOXML
handling, and the existing digital-metrics/report-generator dependencies.
Storage is existing JSON metadata, ClearML model/run metadata, and XLSX contents.
Verification uses pytest, Ruff, strict mypy, import-linter, repository hooks, real
native training/publication, and independent review. No dependencies change.

## Constitution Check

Pass before and after design: typed neutral value objects; SDK stays in adapters;
existing task/output ownership and module layers remain. No upstream modifications,
no historical artifact rewrites, and no new registration requirement for labels.
The current contract index governs task recovery over historical constitution text.

## Project Structure

- `src/clearml_yolo/model_identity.py`: validated identity and checkpoint binding.
- `clearml_native.py`, `clearml_models.py`: publication and source recovery.
- `clearml_results.py`, `result_schema.py`: prediction/context identity.
- `tasks/`: propagation through predict, val, metrics, compare, report, pipeline.
- `comparison/scoring.py`, `clearml_report.py`: evaluation and interactive captions.
- `workbook_identity.py`: annotation, durable identity, and legacy-layout reading.
- `tests/`: source, workbook, evaluation, and task regression coverage.

## Design and verification

See [research](research.md), [data model](data-model.md), and
[report identity contract](contracts/report-identity.md). Independent work owns
source publication, workbook adapters, and evaluation rendering. Parent owns task
integration and verification. Final review uses a fresh read-only context.

## Documentation scope

Update the current contract index, model metadata, task recovery, evaluation
publication, README usage, and feature quickstart. Validate Markdown, local links,
and changed CLI/config examples. Keep live machine evidence in the environment
skill and a portable dated verification summary here.
