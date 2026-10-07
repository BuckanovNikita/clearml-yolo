# Tasks: Readable evaluation plots

## Setup and foundations
- [x] T001 Capture approved scope and design in spec.md, plan.md and contracts/plots.md; validate requirements and coverage.

## US1: Grouped readable charts
- [x] T002 [US1] Add failing behavior tests and implement grouped confusion/PR in src/clearml_yolo/clearml_report.py and tests/test_interactive_evaluation.py (FR-001–003).
- [x] T004 [US1] Add publication slot and role coverage in tests/test_clearml_results.py; implement stable readable slots in src/clearml_yolo/clearml_results.py (FR-004–005).

## US2: Current-model-only publication
- [x] T003 [P] [US2] Test and suppress native validation PR in src/clearml_yolo/native_runtime.py and native callback tests (FR-006).
- [x] T005 [US2] Remove comparison tables while preserving headline values in src/clearml_yolo/clearml_report.py and tests/test_clearml_report.py (FR-004).

## Verification
- [x] T006 Run focused and full repository checks; inspect isolated real publication and browser interactions; record verification-2026-10-07.md.
- [x] T007 Obtain fresh independent read-only review after parent verification; fix and recheck findings.

## Documentation update
- [x] T008 [P] Update affected publication/identity/native contracts, docs/current-contracts.md, README and E2E guidance after implementation (FR-007).
- [x] T009 Validate Markdown, local links and changed examples; record documentation evidence after T008.

## Dependencies and execution
T001 precedes implementation. T003 is independently owned by the native adapter agent.
Parent owns T002/T004/T005; T004 uses T002's optional display_label interface. T006 follows
implementation, T007 follows T006, and T009 follows T008. Documentation may run alongside
verification once implementation behavior is stable. Apply tests before production edits.
