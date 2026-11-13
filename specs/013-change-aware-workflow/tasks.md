# Tasks: Change-aware workflow

## Phase 1: Setup and native analysis

- [x] T001 Inspect current policy and create native spec/design in specs/013-change-aware-workflow/.
- [x] T002 Compare spec, plan and task coverage with constitution; record analysis in this ledger.

## Phase 2: US1 relevant verification

- [x] T003 [US1] Implement one path classifier and bounded test selector in scripts/verification.py.
- [x] T004 [US1] Move hygiene/staging into Taskfile.yml and scripts/hygiene.py; simplify .pre-commit-config.yaml and scripts/git-hook.sh.
- [x] T005 [US1] Exercise disposable routing/history/empty/early-failure scenarios and record dated verification evidence.

## Phase 3: US2 supported coverage and concise guidance

- [x] T006 [P] [US2] Remove effect scanning in scripts/architecture*.py and requested tooling/physical multi-GPU tests in tests/.
- [x] T007 [P] [US2] Reconcile docs/ and five non-release maintained skills with retained contract/check mappings.
- [x] T008 [US2] Collect retained product tests and prove architecture boundaries remain effective.

## Phase 4: US3 release mechanics

- [x] T009 [P] [US3] Implement explicit local/publish Task entrypoints in Taskfile.ops.yml and scripts/release.py; simplify release skill.
- [x] T010 [US3] Integrate semantic-release build environment in pyproject.toml and validate final-pair/refusal behavior in disposable repos.

## Phase 5: Integration and acceptance

- [x] T011 Integrate all task-owned changes, apply safe fixes, run static gates and canonical committed-tip prek pass.
- [x] T012 Complete applicable explicit acceptance and independent review; reconcile final diff with documentation and tasks.
- [x] T013 Record measured reductions, executed outcomes and gaps in verification-2026-11-13.md; commit task-owned changes without releasing/publishing.
- [x] T014 Simplify the six custom skills and remove relative Markdown links from active skill guidance; preserve historical archives and installed Spec Kit files.
- [ ] T015 Verify the documentation follow-up on the committed tip and complete independent meaning-preservation review.

## Dependencies and parallel execution

T001-T002 precede implementation. T003-T005 run sequentially at root. T006-T008,
T007 and T009 can run in parallel with independent file ownership; T010 follows T009.
T011 follows all implementation; T012 follows integration/verification; T013 records
final evidence. Root alone edits shared configuration and makes commits.

## Native analysis, 2026-11-13

Coverage: FR-001→T003-T005; FR-002→T004/T011; FR-003→T006-T008;
FR-004→T009-T010; FR-005→T005/T008/T010-T013. No uncovered requirement or
constitution conflict. No separate documentation checker. Preserve product purity
requirements while explicitly reducing static effect automation. Native extension
hooks are empty. No unresolved specification clarification. Requirement checklist passes.

## Completion evidence

[Verification, review and coverage reductions](verification-2026-11-13.md) records the
actual checks and their limits. Independent review closed all six findings at `4ef5d96`.
Full acceptance and paired compatibility pass; product evidence is reused after the
narrow tooling fixes, which have their own successful command-level regressions and
canonical hooks. No real release/publishing was authorized or performed.
