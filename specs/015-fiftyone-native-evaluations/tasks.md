# Tasks: native FiftyOne evaluations

## Phase 1 — intent and design

- [x] T001 Record approved scope, research, data model and contract.
- [x] T002 Analyze spec/plan/tasks coverage and constitution; no unresolved conflicts.

## Phase 2 — implementation (parallel ownership)

- [x] T003 [P] Add tested neutral report payload and producer enrichment (FR-002,003,007).
- [x] T004 [P] Add tested native backend/results, serialization and subsets (FR-001–004).
- [x] T005 [P] Add tested Python plugin, exact navigation and PR/AP UI (FR-003,004,008).
- [x] T006 Integrate publisher lifecycle and receipt/run links after T003/T004 (FR-001,005–007,009).

## Phase 3 — acceptance

- [x] T007 Real isolated persistence/reload/retry/concurrency and UI acceptance after T003–006.
- [x] T008 Static gates, full regression suite and real metrics/pipeline verification.
- [x] T009 Fresh independent review after parent verification; resolve findings.

## Phase 4 — mandatory documentation

- [x] T010 Update publisher contract, current index, Russian README, integration spec/quickstart and acceptance guidance after implementation.
- [x] T011 Validate Markdown, local links and changed examples; record dated evidence after T007–010.

## Release

- [ ] T012 Run commit/release hooks and publish Git commits/version tag only.
