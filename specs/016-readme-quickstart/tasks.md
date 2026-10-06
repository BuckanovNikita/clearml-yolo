# Tasks: README quickstart

## Phase 1 — Setup and foundation

- [x] T001 Inspect README.md, docs/current-contracts.md, configuration and dependency evidence.
- [x] T002 Record approved requirements and plan in specs/016-readme-quickstart/.

## Phase 2 — US1: primary journey

Independent acceptance: configuration examples resolve and the reader can locate results.

- [x] T003 [US1] Rewrite setup, conversion, cy invocation and results in README.md.

## Phase 3 — US2: migration and discovery

Independent acceptance: tables cover the manual stages, parameter mapping and nine commands.

- [x] T004 [US2] Add migration tables, Mermaid diagram and auxiliary guidance in README.md.

## Phase 4 — Documentation update and validation

- [x] T005 Reconcile docs/development.md references and review retained contract destinations.
- [x] T006 Validate README.md and changed documentation; record dated results in specs/016-readme-quickstart/verification-2026-10-06.md.
- [x] T007 Obtain independent review of the complete diff and record its outcome in specs/016-readme-quickstart/verification-2026-10-06.md.

## Dependencies and implementation strategy

T001/T002 precede T003; T004 follows T003 because both own README.md. T005 and T006
follow the rewrite; T007 follows parent validation. A read-only investigation runs in
parallel with parent artifact preparation; agents own no writes. Deliver US1 first,
then US2, then validate the combined documentation. All FR-001 through FR-006 are
covered by T003 through T007; no application tests or new runtime contracts are needed.
