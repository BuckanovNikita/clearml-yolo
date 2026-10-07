# Tasks: Model report identity

## Setup and foundation

- [x] T001 Record approved intent and inspect contracts in specs/019-model-report-identity/spec.md.
- [x] T002 Add shared identity validation and checkpoint association in src/clearml_yolo/model_identity.py.

## US1: Training source identity

- [x] T003 [P] [US1] Persist/recover finalized model identity in src/clearml_yolo/clearml_native.py and clearml_models.py; test source identity in tests/test_model_identity_sources.py.
- [x] T004 [US1] Carry prediction identity through src/clearml_yolo/clearml_results.py and tasks/predict.py; test stale provenance and source-task preservation.
- [x] T005 [US1] Carry source identities through tasks/metrics.py, tasks/val.py, tasks/compare.py, and tasks/pipeline.py.

## US2: Identified reporting

- [x] T006 [P] [US2] Implement workbook annotation/reading in src/clearml_yolo/workbook_identity.py; verify real multi-sheet files, formulas, styles, print titles in tests/test_workbook_identity.py.
- [x] T007 [P] [US2] Add evaluation/interactive captions in src/clearml_yolo/comparison/scoring.py, result_schema.py, comparison/evaluation_payload.py, clearml_report.py and tests/test_evaluation_identity.py.
- [x] T008 [US2] Integrate paired identities and readers in src/clearml_yolo/tasks/report.py and tasks/compare.py; verify class populations and missing baseline.

## US3: Standalone labels

- [x] T009 [US3] Expose fallback labels in src/clearml_yolo/tasks/ and src/clearml_yolo/configs.py; test missing/custom/recovered identity flows.

## Verification and documentation

- [ ] T010 Run repository gates and native CPU/GPU publication acceptance; record specs/019-model-report-identity/verification-2026-10-07.md.
- [x] T011 Update README.md, docs/current-contracts.md, affected publication/recovery/model metadata contracts, and feature quickstart; validate Markdown, links, and examples.
- [ ] T012 Obtain fresh independent review, address findings, and complete authorized release workflow from docs/development.md.

## Dependencies and parallel work

T002 defines the common value. T003, T006, and T007 have separate file ownership;
T004/T005/T008/T009 integrate their outputs. T010 and T011 precede final T012 review.
Each story's independent acceptance scenarios are in spec.md. Source, workbook,
and rendering tests run independently; combined verification remains parent-owned.
