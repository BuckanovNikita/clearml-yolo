# Tasks: Custom augmentation and universal mosaic

## Phase 1 — Approved specification and architecture

- [x] T001 Record approved requirements, interfaces, native workflow and ownership.
- [x] T002 Validate architecture plan and analyze requirement/task coverage.
- [x] T003 Upgrade Ultralytics/Albumentations floors selectively and check compatibility.

## Phase 2 — Shared augmentation and dataset tooling

- [x] T004 [P] Implement/test pure transform config and validated immutable snapshots.
- [x] T005 [P] Implement/test shared Albumentations geometry, metadata and Mosaic donor policy.
- [x] T006 [P] Implement/test Severstal RLE/component conversion, identity and frozen splits.
- [x] T007 [P] Implement opt-in 15-preset x three-variant native smoke harness.

## Phase 3 — Native and configuration integration

- [x] T008 Integrate raw readers and finalization into DEIM, RF-DETR and Faster R-CNN (T004/T005).
- [x] T009 Integrate owned YOLO dataset/trainer including worker/DDP and mosaic transitions (T004/T005).
- [x] T010 Add visible Hydra profiles, generated examples and strict backend conflict policy (T004).
- [x] T011 Thread frozen JSON through queue snapshots, canonical publication and Agent replay (T010).
- [x] T012 Extend SDK/import/effect contracts with negative coverage and run focused integration checks.

## Phase 4 — Native acceptance

- [x] T013 Retrieve official Severstal inputs and prepare/freeze conversion and split manifests (T006).
- [ ] T014 Execute all 45 smoke scenarios with real optimizer/checkpoint/prediction evidence (T007-T013).
- [ ] T015 Verify downloaded checkpoint/configuration evidence and preserve scoped cleanup receipts.
- [x] T016 Run complete applicable pytest/static/import/dependency compatibility checks.

## Phase 5 — Documentation, review and delivery

- [x] T017 Update README, augmentation/backend/contracts/examples and validate Markdown/links/examples.
- [x] T018 Update and validate portable usage skill source and companion task-owned changes.
- [x] T019 Reconcile diff and architecture record; obtain fresh independent review after verification.
- [ ] T020 Validate architecture acceptance and deliver through checked Git-only release.
- [x] T021 Record separate full Severstal training task, pending explicit post-release approval.

## Dependencies and stopping rules

T004/T005 own the shared interface; T008/T009 cannot invent separate pipeline semantics.
T006/T007 are independent preparation work; parent integrates all results. T014/T015
are required acceptance, not replaceable by mocks. T020 depends on T014-T019 passing.
Full-data training is outside this ledger's execution authorization.

## Resource steering, 2026-10-23

The user requested reduced machine load until the next 00:00 Europe/Moscow, then
clarified that approximately six CPU cores are acceptable. CPU checks share one
six-core affinity pool with low scheduling priority and capped native threads.
GPU smoke execution remains deferred until 2026-10-24 00:00 Europe/Moscow
(2026-10-23 21:00 UTC). No existing workload is stopped or reconfigured.

The user subsequently requested “continue without limits”, lifting this temporary
CPU/GPU restriction before midnight. Native GPU acceptance resumes under the
existing task authorization; unrelated workloads remain untouched.


## Verification checkpoint, 2026-10-24

The complete suite after harness refinements passed 3,226 tests; static/import and
documentation checks passed. T018's usage guidance is validated in an isolated
worktree based on current corp-skills upstream v0.4.3; the original stale checkout's
unrelated edits remain intact. Companion release remains part of T020, not a claim
of publication. Native receipts and remaining access gates are tracked in
[evidence/verification.md](evidence/verification.md) and
[evidence/native-smoke.json](evidence/native-smoke.json).

Fresh independent source/architecture review accepted the integrated code with no
blocking findings; see [evidence/review.md](evidence/review.md). Native matrix and
cleanup gaps still block T020; code review does not waive them.

## Native checkpoint and cleanup, 2026-10-24

T014 has 39/45 required pretrained GPU passes. DEIMv2-L/X's six scenarios require
the authorized DINOv3 Small/Small+ files documented in the quickstart. Six separate
random-initialization probes all failed upstream before any optimizer update and
do not replace pretrained acceptance. The official dataset access issue is resolved.

For T015, all 39 passed scenarios have downloaded artifact, checkpoint reload,
initialization and archive-hash evidence. Both owned GPU projects and the invocation
directory were cleaned after archive verification; the final listing is empty.
T015 remains open for the six missing pretrained scenarios. The complete code and
fresh review remain unchanged; acceptance validation correctly rejects the pending
native gate. T020 and both application/companion releases remain pending.

## Explicit release request, 2026-10-24

After the native gap and pending release were disclosed, the user requested
“make a release”. [The release record](evidence/release.md) preserves that scoped
authorization and the remaining verification limits. Native/architecture results
are not relabeled as passing. The delivery portion of T020 proceeds under this
exception; its complete-acceptance portion remains pending.

- [x] T022 Deliver the application and usage companion through checked Git-only
  release under the user's explicit exception; verify remote refs and preserve
  the incomplete native acceptance evidence.

Application v0.39.0 and usage collection v0.4.4 were atomically pushed with
annotated tags and verified remote refs. Normal application hooks passed for
both the contributor and version commits; companion documentation checks passed.
The [delivery receipt](evidence/release.md) records identities, the investigated
interpreter crash, preserved local overrides and the remaining native gap.
T020's delivery portion is complete under the explicit exception; its full
acceptance portion and T014/T015 remain open.
