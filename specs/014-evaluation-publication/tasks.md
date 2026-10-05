# Tasks

## Foundation

- [x] T001 Record approved requirements and interface/ownership contracts in spec.md, plan.md and contracts/interfaces.md.

## US1: Complete evaluation evidence

- [x] T002 [P] [US1] Test and implement lineage/export in src/clearml_yolo/result_schema.py, result_export.py and tests/test_result_export.py.
- [x] T003 [US1] Preserve prepared-index mappings and exact evidence in src/clearml_yolo/comparison/scoring.py and dedicated tests.
- [x] T004 [P] [US1] Implement durable context collection and pre-finalization publication in src/clearml_yolo/clearml_results.py and clearml_session.py.
- [x] T005 [US1] Wire tasks, apps, artifact_names.py and import contracts; verify exact standalone, pipeline and skipped-stage inventories.

## US2: Interactive plots

- [x] T006 [US2] Implement public matching PR reconstruction/AP50 parity in src/clearml_yolo/comparison/pr_curves.py and tests/test_pr_curves.py.
- [x] T007 [P] [US2] Implement four confusion views and per-class PR in src/clearml_yolo/clearml_report.py and tests/test_interactive_evaluation.py.

## US3: Names and model metadata

- [x] T008 [P] [US3] Test and implement collision resolution in src/clearml_yolo/clearml_naming.py and tests/test_clearml_naming.py.
- [x] T009 [US3] Preserve owned model handle and verify calibration association/readback in src/clearml_yolo/clearml_native.py and dedicated tests.
- [x] T010 [US3] Wire name resolution, stable routing and calibration provenance through session/apps/tasks with integration tests.

## Documentation update and acceptance

- [x] T011 Update affected publication/model contracts, docs/project-contracts.md, docs/current-contracts.md, README.md and .agents/skills/running-end-to-end-tests/SKILL.md after T005/T007/T010.
- [x] T012 Validate Markdown, local links and changed examples; record in verification-2026-10-05.md.
- [x] T013 Run pytest, Ruff, mypy, import-linter and required hooks; record evidence.
- [x] T014 Verify native CPU/GPU execution, download ClearML artifacts/model, inspect plots/metadata/telemetry and clean task-owned resources.
- [x] T015 Obtain fresh independent read-only review after parent verification; fix findings and reverify.
- [x] T016 Apply applicable Git-tag-only release workflow after acceptance; preserve local sources.

## Dependencies

T001 precedes all implementation. T002/T003/T006 share A; T007 B; T008/T009 C;
T004 parent runs concurrently. T005/T010 integrate accepted interfaces. T011 runs in
parallel with parent tests. T012–T015 establish acceptance before T016.
