# Tasks: Test quality and GPU controls

## Definition and architecture

- [x] T001 Capture approved scope, assumptions, interfaces and ownership in spec.md and plan.md (FR-01–10).
- [x] T002 Validate architecture.json and analyze requirement/task coverage before implementation.

## Implementation and regression evidence

- [x] T003 Parent: reproduce absent capabilities, implement local/interpreter preflight and tests (US1; FR-01–02).
- [x] T004 [P] Queue: implement typed controls, physical identity selection, owner holds, full-claim release and CLI (US2; FR-03–06).
- [x] T005 [P] Queue: test cross-root ownership, admission races, stale claims, interrupted release and compatibility fencing (US2; FR-03–06).
- [x] T006 [P] DDP: implement explicit GPU marker/options, real direct/queued native scenarios and retained evidence (US3; FR-07–08).
- [x] T007 [P] DDP: offline harness tests prove selection, failures, evidence capture and cleanup without GPU side effects (US3; FR-07–08).
- [x] T008 [P] Quality: add composed workflows and generated identity/evaluation/queue invariant tests (US4; FR-09).
- [x] T009 Parent: add development dependencies, coverage configuration and test-tool ownership checks without runtime upgrades (FR-10).
- [x] T010 Parent: integrate queue preflight and demonstrate selected semantic faults are caught (FR-01, FR-09).

## Verification and documentation

- [x] T011 Parent: run full offline pytest and relevant static/import/architecture checks; reconcile complete diff.
- [x] T012 DDP/parent: document exact remote selection/archive commands and validate examples.
- [x] T013 Parent: update queue, runtime, development, current contract and README guidance; validate Markdown/links.
- [x] T014 Parent: update and validate canonical corp-skills portable usage/evaluation guidance; record source identity.
- [ ] T015 Fresh independent review after integration and checks; resolve findings and validate local architecture acceptance.
- [ ] T016 External: obtain and review user-supplied physical multi-GPU results; retain an explicit acceptance gap until then.

T015: Both independent reviews and local checks passed; findings were resolved.
The reconciled architecture record passes planning validation, while acceptance
retains the unexecuted physical GPU check required by T016. See
[dated verification](verification.md); no mocked result replaces that check.

## Authorized local delivery — 2026-10-15

- [x] T017 Parent: integrate current upstream documentation, run commit/release hooks, inspect package metadata and distribution, and push the tool branch plus annotated release tag.
- [x] T018 Companion/parent: finalize, review, commit and publish the prepared portable usage-skill release after the tool release is verified.
- [x] T019 Parent: record release refs and local checks; preserve local overrides and unrelated work; leave physical acceptance open.

The user explicitly requested local completion and release before supplying the
other machine's results. T015's remaining overall acceptance gate and T016 remain
external; they do not represent unperformed local implementation or review.
See [release evidence](release.md).
