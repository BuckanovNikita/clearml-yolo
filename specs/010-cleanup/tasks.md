# Tasks: Simplify maintenance and complete pending delivery

Inputs: [specification](spec.md), [plan](plan.md), [architecture](architecture.json).
Checkboxes record current execution status. The original planning ledger established
intent; dated checkpoints below and execution.md supply actual check evidence.

## Phase 1 — Baseline and implementation gates

- [x] T001 Reconcile latest CY, queue and portable-guidance sources with both dirty worktrees; preserve originals and establish an isolated implementation workspace. Record source identities and transferred/excluded changes. (FR-001/002)
- [x] T002 Reconcile this plan and architecture record against that workspace; record bug assessments, exact stream ownership and candidate dispositions; validate architecture plan and run Spec Kit consistency analysis before implementation. (FR-009/011)
- [x] T003 Capture canonical baseline with source/interpreter/dependency identity, case counts and existing per-command timings; benchmark targeted release/graph setup separately with pytest duration reporting before optimization. Use passing canonical evidence for applicable DINOv3 prepublication checks; record failures without treating them as a baseline pass. Final per-case canonical diagnostics arrive in T016. (FR-007/010)

## Phase 2 — Pending DINOv3 amendment

- [x] T004 Finish existing 009 DINOv3 T020 documentation, attribution/notices and authoritative portable guidance, preserving prior evidence and checking examples. (FR-002/008)
- [x] T005 Finish existing 009 T021 prepublication canonical/current/proposed pairing and fresh independent review against the actual snapshot/source; reuse T003 only for matching inputs. (FR-002/010)
- [x] T006 Complete existing 009 T022 authorized immutable snapshot publication, hosted-byte verification and deliberate package-pin update. Reuse unchanged verified archives; refuse conflicting published identities. Defer 009 T023 code delivery to T022 below. (FR-002/010)

## Phase 3 — Runtime stream

- [x] T007 [P] [US2] Capture missing-input export-preview regressions for all three operations, plus valid/deferred and no-effect cases, in existing documentation validation tests. (FR-003)
- [x] T008 [US2] Extract the exact pure export-presence predicate in the existing core module; retain the runtime method delegating to it and invoke it from preview validation without resolving expressions or adding IO. Verify T007 and original runtime messages/order. (FR-001/003)
- [x] T009 [US1] Remove unused metrics methodology-frame helper and its sole import; retain active reporting ownership and verify existing metrics/reporting tests. (FR-005)
- [x] T010 [US1] Consolidate Hub blob-to-snapshot symlink/copy publication inside the existing adapter, with an explicit validator callback; verify containment, atomic replacement, fallback validation and source preservation. (FR-005)

## Phase 4 — Tests and tooling stream

- [x] T011 [P] [US2] Reproduce release-fixture configuration leakage; restrict copied TOML to semantic-release tables and children. Verify with/without local overrides and subsequent unrelated tables; retain protected-lock and real-hook checks. (FR-004)
- [x] T012 [US3] Transfer unique ClearML/backend/profile assertions into the stronger all-command/all-preset self-containment test, then remove eight overlapping round-trip and four warning cases. (FR-006)
- [x] T013 [US3] Replace the 54-case dynamic-import syntax/SDK product with six minimal-graph syntax cases and nine configured SDK ownership integrations. Preserve shadowing/type-only forms and each negative contract. (FR-006/009)
- [x] T014 [US3] Share immutable import-graph/options setup across affected tests, deep-copying before contract mutation or injected edges; verify unchanged rejection and fresh-process isolation. (FR-006/009)
- [x] T015 [US3] Benchmark module-seeded release repositories copied into each isolated Unicode/spaced test directory, retaining independent writable Git state, environment cleanup and real hooks. Adopt only if demonstrably faster; otherwise record rejection and keep current isolation. (FR-007)
- [x] T016 [US3] Add `--durations=25` to canonical pytest reporting without selection changes. Preserve byte-based input/dependency fingerprints, partial-index rejection, interruption invalidation and generated-release recovery; run existing verifier/lifecycle regressions. (FR-007)

## Phase 5 — Documentation update and parent integration

- [x] T017 [US4] Reconcile schema-3 summaries, annotate superseded bulk upstream fallback, correct stale release claims, clarify immutable manifest identifiers, and complete command/status navigation. Preserve historical native limitations and standalone selected-model behavior. (FR-008)
- [x] T018 Update affected Russian README, current topic/index guidance and authoritative portable usage sources; validate Markdown, local links, examples and companion metadata, or record inspected no-change reasons. (FR-008)
- [x] T019 Parent integrates both streams and pending pin; inspect complete task-owned changes, preserve unrelated work, and compare actual counts/implementation/setup costs with T003. Record each candidate as simplify/remove/retain/unresolved and its acceptance evidence. (FR-001/005/006/007/011)

## Phase 6 — Acceptance and eventual delivery

- [x] T020 Run final canonical verifier, documentation verifier, `cy-docs --check`, affected browser acceptance and mutation applicability/checks. Repeat scoped fresh-cache Hub restoration and genuine offline DINOv3 loading after T010; verify latest/current/proposed CY–queue normal resolution, installed metadata, integration/static checks. Record every skip and unavailable check explicitly. (FR-010)
- [x] T021 Obtain fresh independent review after parent verification; resolve findings, rerun affected checks, reconcile full diff/ledger and architecture record, then validate architecture acceptance. Historical hardware exceptions retain their scoped limits. (FR-009/010/011)
- [ ] T022 Complete 009 T023 and the cleanup's authorized code delivery together: preserve/remove exact local uv sources through final checks and hooks, stage task-owned changes only, create native Conventional Commit/version/annotated tag, refresh final installed version pairing, push intended refs and verify them; restore overrides unstaged on success or failure. No code GitHub Release or package publication. (FR-001/002/010/011)

## Dependencies and bounded ownership

T001 precedes T002; T002 gates implementation. T003 precedes test-cost changes and
supplies matching baseline evidence to T005. T004 precedes T005; T005 precedes
T006. Runtime T007–T010 and test/tooling T011–T016 may proceed independently after
T002/T003 with exclusive ownership. T007 precedes T008. T012–T016 preserve baseline
evidence from T003. Parent owns T001–T006 and T017–T022, shared records and integration.
Runtime owns only core export/preview/metrics/Hub implementations and their focused
tests; test/tooling owns only release fixtures, configuration/architecture/isolation
tests and duration diagnostics. Children may not delegate or edit another owner's
paths. T017/T018 reconcile final interfaces after T006/T008/T016; T019 follows all
stream work; T020 follows T019; T021 follows successful T020; T022 follows acceptance.

Use Sol orchestration with inherited parent model/effort. A fresh review context
assesses the integrated diff; requested settings are not runtime-setting evidence.
Missing mandatory checks or review remain acceptance gaps. No task above authorizes
execution during the current planning-only request.

## Requirement and success-criterion coverage

| Requirement | Tasks |
| --- | --- |
| FR-001 | T001, T008, T019, T022 |
| FR-002 | T001, T004–T006, T022 |
| FR-003 | T007–T008 |
| FR-004 | T011 |
| FR-005 | T009–T010, T019 |
| FR-006 | T012–T014, T019 |
| FR-007 | T003, T015–T016, T019 |
| FR-008 | T004, T017–T018 |
| FR-009 | T002, T013–T014, T021 |
| FR-010 | T003, T005–T006, T020–T022 |
| FR-011 | T002, T019, T021–T022 |
| SC-001 | T007–T008, T011, T020 |
| SC-002 | T009–T010, T019–T020 |
| SC-003 | T012–T014, T019–T020 |
| SC-004 | T003, T015–T016, T019 |
| SC-005 | T004–T006, T017–T018, T020, T022 |
| SC-006 | T020–T022 |

## Execution checkpoint — 2026-11-01

T001 established the isolated cleanup worktree from fetched e82cc49 and a separate
latest queue worktree at 2fbaed2 (0.1.6). T004–T006 are satisfied by the already
delivered DINOv3 amendment in that newer source, not by newly executing publication.
The original 009 ledger and acceptance evidence are preserved. The reviewed plan
was copied into the isolated workspace; originals were not altered.

The environment was synchronized from the frozen lock with approved external
source copies. Both external source SHAs matched maintained approvals. Initial
normal resolution lacked the private source packages; explicit local inputs resolved
it. A subsequent unconstrained install attempt was interrupted before completion,
then frozen synchronization established the baseline package view. Installing the
latest queue normally succeeded and pip check reported compatible packages.
Canonical forced baseline verification is running; no pass is claimed yet.

Runtime stream T007–T010 has parent-inspected code and focused agent evidence; final
canonical/native/review acceptance remains T020/T021. Runtime changed only the six
assigned core/preview/metrics/Hub and focused test paths. T017 maintained contract
corrections and supersession links pass Markdown/link checking.

The first baseline suite completed but its receipt was refused for changed installed
inputs; T003 remains open until the prepared stable rerun passes. Separate immutable
baseline/final trees and private installed-package copies now allow their verification
runs in parallel. T020/T021 acceptance still depends on both results, final integration
evidence and fresh review. Detailed measurements and limitations are in execution.md.

## Stable baseline and integration correction

T003 stable canonical verification passed with an unchanged-input receipt; pytest
reported 4571 passed, 30 skipped and 81 deselected. The first integrated final suite
caught the existing AST-helper import guard, so no receipt was recorded for that run.
The correction restored the helper to upstream-identical stdlib/grimp ownership and
placed SDK construction in lazy pytest composition; all 473 affected tooling/graph/
configuration/isolation cases and scoped Ruff/mypy passed. No guard was loosened.
The final canonical gate and fixture-dependent mutation selection are being refreshed.

## Discovered native cleanup bug — required release dependency

The second final canonical run failed the unchanged native double-fork cleanup test:
4535 passed, one failure, 30 skipped, 81 deselected in 1359.80 seconds; no receipt.
A bounded investigation reproduced the same timeout under four owned sibling churn
workers after all owned descendants had exited. This is a real discovered bug, not
permission to retry the suite until green or weaken deadlines. Original task history
above remains a checkpoint; the following tasks precede T020/T021/T022 acceptance.

- [x] T023 Assess the observed native-process churn failure and record scoped architecture, reproduction and safety constraints before implementation.
- [x] T024 Add deterministic failing topology regressions and implement only identity-safe caller-scoped native discovery in the existing runtime adapter; preserve global historical recovery, ownership fences, helper protection and all public interfaces/deadlines.
- [x] T025 Verify original/stress/native/subreaper/cancellation/capability paths, obtain focused independent safety review, refresh affected mutation acceptance and repeat T020 canonical checks before final T021 review and T022 delivery.

T023 precedes T024. A bounded runtime implementer owns only process_tree.py and the
agreed native/subreaper regression files; no delegation or unrelated edits. Parent
owns evidence/architecture/ledger integration. T025 and the final complete review
are mandatory release dependencies. The code remains a backward-compatible fix.

## Native cleanup implementation and focused acceptance

T024 is implemented without public/dependency changes. Parent repeated all 64 scoped
process regressions (45.97 seconds), Ruff/mypy, original double-fork (2.96 seconds)
and the original four-sibling stress harness (2.263 seconds, exit zero). Fresh
native_cleanup_safety review returned ship, no actionable findings; see the bug's
[verification](../../docs/bugs/cleanup-native-process-churn/test.md). Mutation inputs
and dependencies remain unchanged; recorded 433-mutant evidence is applicable.
T025 remains pending final canonical acceptance; final release review remains T021.

## Complete verification checkpoint

T020 and T025 passed: final canonical receipt 38ae7edf6f434071b262a7cea5027940,
4545 passed/30 skipped/81 deselected; documentation/catalog/browser/native checks,
scoped mutation acceptance and fresh latest-code proposed 0.44.6 / queue 0.1.6
integration (544 passed, 139.91 seconds) are recorded in execution.md. Exact root
metadata bytes were restored; original workspaces remain preserved. T021 final
independent review/architecture acceptance and T022 delivery remain pending.

## Independent integrated acceptance

Fresh cleanup_final_acceptance review returned ship with no actionable findings.
The reviewer independently checked canonical log hashes/returns, all mutation outcomes
and survivor equivalences, architecture and retained negative/unique coverage. Parent
reconciled all task-owned paths; see acceptance.md. T021 is complete after the linked
architecture validator passes acceptance. T022 native hooks, final committed pairing
and GitHub ref verification remain mandatory before delivery completion.
