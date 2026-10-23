# Tasks: Portable training and extracted queue

## Setup and contracts

- [x] T001 Inspect baseline, current changes, workflow, package/configuration/runtime contracts and portable usage source.
- [x] T002 Record spec, research, architecture, interface/data contracts and bounded parallel ownership in specs/003-portable-training.
- [x] T003 Validate architecture plan records and analyze requirement/task coverage before implementation.

## US1 — Queue extraction (FR-001–003, FR-011)

- [x] T010 [P] Move queue modules and tests into sibling cy-queue; establish source metadata, import contracts, README and docs/architecture.json.
- [x] T011 [P] Preserve wire/config/lock identities, lifecycle and installation checks; add pipeline/train selection and compatibility tests.
- [x] T012 Parent integrates CY dependency removal, import contracts and mixed tests; verify queue tests and cross-package source installation.

## US2 — Agent replay (FR-004–005)

- [x] T020 [P] Add failing bare-entrypoint replay/backend/precedence tests in CY tests/test_agent_replay.py.
- [x] T021 [P] Implement detached replay snapshot and pre-validation startup in ClearML session/common entrypoint, retaining task metadata and failures.
- [x] T022 Verify no queue imports/configuration, logical CUDA settings and canonical selector preservation.

## US3 — Model assets (FR-006–010)

- [x] T030 [P] Implement typed assets and HTTP/cache/archive resolver with local fixture failures, fallback, concurrency and manual-placement tests.
- [x] T031 [P] Verify upstream asset selection and DEIM manifest; integrate native local loading for all non-YOLO presets, preserving explicit overrides.
- [x] T032 Parent integrates execution-copy resolution and separate provenance; verify null selectors and unchanged YOLO behavior.

## Integration and documentation

- [x] T040 Run both repositories' tests, Ruff, strict mypy, import contracts/negative cases and applicable hooks; fix integration findings.
- [x] T041 Execute short native training by family and real extracted queue/Agent runs, checking downloaded task/model publication; record unavailable Artifactory connectivity.
- [x] T042 Update Russian READMEs and queue migration/backend/assets/filesystem/Agent/architecture/baseline contracts; validate Markdown, links and examples.
- [x] T043 Update portable corp-skills usage/evaluation guidance and validate source package; commit companion changes after checks.
- [x] T044 Obtain fresh independent review after parent integration/verification; resolve findings, reconcile diff and validate architecture acceptance.
- [x] T045 Complete CY Git-only release and verify refs; commit new cy-queue repository without remote creation/publication/deployment; preserve local overrides and clean task-owned resources.

## Dependencies

T003 gates T010/T020/T030. Queue and asset workers have disjoint ownership; parent implements Agent replay in parallel. T012 depends on T010–T011, T032 on T030–T031. T040–T043 follow integration, T044 follows checks, T045 follows acceptance. Checks unavailable or failing remain open.

## Acceptance checkpoint, 2026-10-23

Implementation and software verification are complete. Direct pretrained training
and published-checkpoint reload passed for all three affected families; bare real
Agent training and pipeline execution passed. T041 remains open only for physical
extracted-queue execution: current GPU occupancy exceeds the unchanged admission
limit. Live Artifactory connectivity is explicitly unavailable, not claimed passing.

T043's source edits, package checks and fresh skill evaluation passed; its companion
commit/release waits for CY acceptance. T044's fresh code/architecture review returned
ship after one corrected queue validation defect, and complete diff reconciliation
is recorded. Architecture acceptance remains failing only the required physical
queue check. T045 therefore has not started: no feature commit, tag or push exists.
The intended compatible versions were verified in an isolated candidate source
installation; active-environment refresh remains part of actual delivery.

See [integration evidence](evidence/2026-10-23-integration.md),
[independent review](evidence/2026-10-23-review.md) and the recorded
[unreproduced interpreter failure](evidence/2026-10-23-interpreter-crash.md).

## Resumed acceptance checkpoint, 2026-10-23

T041 is complete with [real train and pipeline queue evidence](evidence/2026-10-23-live-queue.md).
The normal worker rejected the busy GPU under its unchanged 2 GiB admission rule;
real execution/publication and acknowledged first-device retention passed under a
private 16 GiB test ceiling. This does not claim physical multi-GPU release or idle
production admission. Fresh independent review accepted the evidence and cleanup.
The earlier checkpoint above remains the history of the initial preflight.

T043's integrated portable-skill candidate passed its fresh review and all package
checks, then received local companion commit `05b5156`. Its Git-tag delivery follows
CY publication. Both repositories' architecture acceptance validators passed after
reconciliation with the final code review and live evidence, completing T044.
T045 now owns release, compatible active-environment refresh and final delivery receipts.

## Delivery closure, 2026-10-23

T045 completed: CY feature `ad6a8ec` and automatic release `8caafcd` passed hooks;
annotated `v0.38.0` and master were pushed and remote refs verified. The new queue
ends at verified Conventional Commit `1be96a6` without a remote or tag. The active
environment was refreshed source-first to CY 0.38.0 and queue 0.1.0; dependency,
entrypoint and resource checks pass. Exact local overrides and unrelated work were
preserved. [Delivery evidence](evidence/2026-10-23-delivery.md) records the outcome
and retains all scoped verification limitations.

The portable usage collection was then published as annotated `v0.4.3`, with final
evidence commit `593f4e9` and verified remote refs. Its original dirty checkout was
preserved; no installed-skill export was requested or performed.
