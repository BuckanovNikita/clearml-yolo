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
- [x] T015 Verify the documentation follow-up on the committed tip and complete independent meaning-preservation review.

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

## Architecture reduction follow-up

- [x] T016 Record approved policy changes and implementation ownership in native artifacts.
- [x] T017 [P] Convert fixed dynamic imports and adapt affected product tests.
- [x] T018 [P] Extend product imports, entrypoints and target-producer coverage.
- [x] T019 Replace scanners with declarative checks and remove unused dependencies.
- [x] T020 Reconcile authoritative guidance and native consistency analysis.
- [x] T021 Verify integrated product/static checks and final committed inputs.
- [x] T022 Complete fresh independent review and record acceptance gaps and evidence.

T016 precedes T017–T020; T021 follows integration; T022 follows verification.
Approved retirements are explicit specification changes, not assertions of equivalent
static coverage. Historical completion evidence above applies to the earlier scope.

### Follow-up native consistency analysis

The explicit user-approved reduction supersedes Principle II's blanket acyclic-helper
and closed core-dependency enforcement for this task. Existing dependency directions
and effect ownership remain. Installed `.specify/` sources are intentionally unchanged;
this records the user instruction precedence rather than silently amending tooling.
T017 covers lazy import compatibility; T018 covers exercised runtime contracts; T019
covers retained declarative rules; T020 records approved retirements; T021–T022 own
verification and independent comparison. No new tooling tests or custom scanners.
Ruff's installed TID251 rejects import_module aliases and qualified builtins.__import__,
but bare __import__ is outside its enforcement and remains a review obligation.

Follow-up completion: [architecture reduction evidence](architecture-reduction-2026-11-13.md)
records the full-suite fixture failures, successful targeted repair, reused unaffected
results, live CPU/FiftyOne outcomes, paired compatibility, passing final hooks and fresh
independent review. No required selected check remains deferred or failed.

## Skill and verification consolidation

- [x] T023 Record approved behavior changes, evidence scope and write ownership.
- [ ] T024 [P] Consolidate release inputs, conditional pairing and Task stages.
- [ ] T025 [P] Retire environment helpers, preserve lifecycle exports and fix smoke identity.
- [ ] T026 [P] Consolidate four skills and reconcile current policies/contracts.
- [ ] T027 Remove exploration-only hook/profile and verify deterministic product properties.
- [ ] T028 Integrate, run selected static/disposable/live checks and committed-tip pipeline.
- [ ] T029 Independent post-verification review, cleanup and dated evidence.

T023 precedes T024–T027; T028 follows integration; T029 follows verification.
Selection: compare 5044d23 with task tip for this bounded follow-up, accounting for the
whole branch's prior dated evidence. No product/runtime/dependency source changes are
planned, so full coverage, GPU, chart rendering and CY/queue pairing are unselected.
Lifecycle/smoke live checks and release command scenarios are required. No new
machine-readable receipt or documentation checker. Native extension hooks are empty;
existing requirements checklist has no unchecked items. Earlier implementation records
remain historical; the approved consolidation intentionally reduces automatic enforcement.
