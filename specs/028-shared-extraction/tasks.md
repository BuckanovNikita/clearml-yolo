# Shared extraction tasks

## Setup and foundations

- [x] T001 Inspect three source trees, instructions and existing changes; record scope in plan.md.
- [x] T002 [P] Capture pre-extraction library and application compatibility evidence in baseline-2026-10-12.md and library dated evidence.
- [x] T003 Validate architecture.json and each library's architecture plan before runtime changes.

## US1 — Evaluation and statistics

- [x] T004 [P] [US1] Add digital-metrics fixed evaluation/shared AP observations and compatibility tests in external/digital-metrics.
- [x] T005 [P] [US1] Add paired statistics and explicit-path single-save rendering in external/digital-metrics.
- [x] T006 [US1] Integrate evaluation and PR adapters in src/clearml_yolo/adapters/evaluation.
- [x] T007 [US1] Add a neutral comparison statistics seam and optional capability composition, preserving existing core calls and dependency constructors.

## US2 — Reporting

- [x] T008 [P] [US2] Add reporting v2 structured inputs/direct presentation, statistical workbooks and OOXML support in external/report-generator.
- [x] T009 [US2] Integrate src/clearml_yolo/adapters/reporting wrappers while preserving identity schema and recovery.

## US3 — Parity and acceptance

- [x] T010 [US3] Verify unchanged library suites, new APIs, scientific/workbook baselines and app integration in tests/test_shared_extraction_compatibility.py and affected suites.
- [x] T011 [US3] Run application checks, import contracts and negative architecture cases; record evidence.md.
- [x] T012 [US3] Inspect integrated diffs and obtain fresh independent review; reconcile architecture records and validate acceptance.

## Documentation and delivery

- [x] T013 Update docs/development.md and docs/current-contracts.md plus library API documentation; record dependency revisions deliberately.
- [x] T014 Validate changed Markdown, links and command/config examples; record evidence.md.
- [x] T015 Complete applicable task-scoped commit/release workflow after required checks; preserve unrelated changes and publish Git tags only.

Dependencies: T002/T003 precede implementation. T004/T005 and T008 are independent.
T006/T007 follow metrics APIs; T009 follows reporting APIs. Integration and verification
precede T012; documentation and its checks precede delivery. No completed history is rewritten.
