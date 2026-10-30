# Tasks: Batch estimation and native distributed training

Input: [plan](plan.md), [specification](spec.md), [architecture](architecture.json).

## Setup and foundations

- [x] T001 Inspect implementation, existing changes and three bounded contract reviews; record specs/006-batch-training/research.md (FR-010, FR-011).
- [x] T002 Record specification, architecture and check gates in specs/006-batch-training/ (FR-001–FR-011).
- [x] T003 Implement typed worker request/results and supervised lifecycle in src/clearml_yolo/adapters/runtime/ with tests/test_training_workers.py (FR-007, FR-010).
- [x] T004 Extend explicit boundaries and negative checks in .importlinter and tests/test_architecture.py (FR-010).

## US1: Estimate and reuse capacity

- [x] T005 [P] [US1] Implement pure catalogue/search/compatibility in src/clearml_yolo/core/batch_estimation.py and tests/test_batch_estimation.py (FR-001–FR-005).
- [x] T006 [US1] Implement atomic locked catalogue storage in src/clearml_yolo/adapters/storage/batch_estimates.py with interrupted/concurrent/resume tests (FR-004).
- [x] T007 [US1] Implement GPU identity/idle/contamination telemetry and fresh-process real probes in src/clearml_yolo/adapters/runtime/ and backend probe modules (FR-002, FR-003).
- [x] T008 [US1] Add injected estimator ports, use case and CLI in src/clearml_yolo/application/ and src/clearml_yolo/entrypoints/batch_estimate.py, plus pyproject.toml entrypoint (FR-001–FR-004).
- [x] T009 [US1] Resolve null after dataset/device selection in src/clearml_yolo/adapters/integrations/; preserve requested replay and chosen provenance with tests (FR-005, FR-006).
- [x] T010 [US1] Verify worker-side null resolution and queue snapshot/handoff compatibility in tests/ and current sibling queue source (FR-006, FR-007).

## US2: Distributed native training

- [x] T011 [P] [US2] Add DEIM rank initialization, sharding and native probes in src/clearml_yolo/adapters/deim/ (FR-003, FR-007).
- [x] T012 [P] [US2] Add RF-DETR external Lightning DDP, per-rank batch and probes in src/clearml_yolo/adapters/rfdetr/ (FR-003, FR-007).
- [x] T013 [US2] Add Torchvision DDP accumulation/EMA, unique validation and checkpoint ownership in src/clearml_yolo/adapters/torchvision/ (FR-007).
- [x] T014 [US2] Integrate owner publication and first-GPU inference in src/clearml_yolo/adapters/integrations/detectors.py (FR-007).

## US3: FCOS

- [x] T015 [P] [US3] Extract shared Torchvision machinery and implement six FCOS models in src/clearml_yolo/adapters/torchvision/ and src/clearml_yolo/adapters/fcos/ with regression tests (FR-008).
- [x] T016 [US3] Extend core registry, assets, augmentation and detector routing while preserving export scope in src/clearml_yolo/ (FR-008).
- [x] T017 [US3] Verify native pretrained loading, finite backward and prediction/checkpoint round trips for all six presets in tests/ and dated evidence (FR-008).

## US4: Configuration export

- [x] T018 [P] [US4] Fix schema collisions, add ordinary packaged defaults and export dependency closure in src/clearml_yolo/entrypoints/hydra/ (FR-009).
- [x] T019 [US4] Verify all commands/models/profiles, self-containment, legacy trees, precedence, collisions and invalid values in tests/test_config_tree.py and related config tests (FR-009).

## Documentation and acceptance

- [x] T020 Update Russian README.md, maintained docs/ contracts and canonical corp-skills usage guidance; validate examples/links/metadata (FR-011).
- [x] T021 Run canonical scripts/verify.py, --docs and applicable scoped mutation; record specs/006-batch-training/evidence/verification.md (FR-010, FR-011).
- [ ] T022 Execute serialized estimator matrix and native distributed/FCOS acceptance using the completed T026 harness; record failures and unavailable multi-GPU evidence honestly (SC-001–SC-005).
- [x] T023 Verify latest paired CY/queue source and proposed versions with normal resolution and integration/static checks (FR-011).
- [ ] T024 Obtain fresh independent reviews after parent integration/checks, resolve findings, reconcile architecture and ledger (FR-010, FR-011).
- [ ] T025 Complete authorized commit and annotated-tag/push workflow only after acceptance; preserve local uv sources and dependency revisions (FR-011).
- [x] T026 Implement the missing opt-in physical DDP harness for DEIMv2, RF-DETR, Faster R-CNN and FCOS, with real rank/publication observations, fault recovery and offline harness contract checks (FR-007, SC-003).

## Dependencies and parallel execution

T001/T002 precede implementation. T003 and T005/T015/T018 can proceed independently
with exclusive files. T011–T014 depend on worker interfaces; T006–T010 depend on policy
records. Parent owns shared registry/import/composition edits. T017/T022 use one GPU
owner. Documentation and isolated queue verification can run concurrently with tests.
T024 follows integration/verification; T025 requires every acceptance gate, including
real multi-GPU evidence. No bounded agent delegates further.

## Integration checkpoint (2026-10-26)

Checked implementation tasks have focused executable evidence; they do not imply
physical multi-GPU acceptance. All three native worker families have CPU/Gloo or
Lightning evidence. The first two fresh reviews found and verified fixes for
legacy automatic devices, YOLO CSV-policy cache matching and final event draining.
At this checkpoint T007/T021–T025 remained open until native probes, complete
verification, final review/reconciliation and their respective acceptance gates
finished. Paired current-source versions had passed normal resolution and queue
checks; proposed release-version verification was still pending.

All six FCOS presets subsequently passed actual pretrained CPU training and copied
checkpoint prediction in fresh processes; see [the dated evidence](evidence/fcos-pretrained.md).
That completes T017 without claiming CUDA, multi-GPU or detector accuracy. The
additional memory review found that allocator peaks must include a separately
observed non-allocator envelope; T007 includes its correction and regression.

A later acceptance audit found that the existing physical DDP suite only supports
YOLO. T026 is implementation work available without new hardware and precedes the
four native families' T022 execution. It extends only test helpers/explicit opt-in
cases, reusing the production worker boundary without changing application APIs.
Its real CUDA/ClearML effects remain behind the existing explicit acceptance flags;
ordinary verification checks commands, evidence validation and failure rejection.

The final telemetry implementation and fresh ownership-scan correction subsequently
passed focused checks and independent re-review, completing T007 implementation.
Physical validation remains T022. Refreshed latest-source snapshots with proposed
CY 0.41.0/queue 0.1.2 passed normal resolution, exact installed metadata, 512 queue
tests and static/import checks, completing T023. Real package versions remain
unchanged; missing physical acceptance still blocks T025.

T026 subsequently passed 46 parent offline tests and fresh independent review.
The reviewer reproduced and verified a correction for RF-DETR minimum dataset
repetition using the installed native loader at two, three and four ranks.
The sixteen physical scenarios are implemented and collected, but remain unexecuted
under T022; code-review acceptance does not waive the hardware gate.

Final canonical run `98ac228d6f9d468dbd654f85ea5b4756` passed with a valid
unchanged-input receipt: 3,940 tests passed, 30 skipped and 81 opt-in cases
deselected; static and all 50 import checks passed. Documentation checks and scoped
mutation applicability are recorded in dated evidence, completing T021. Fresh
reviews and diff reconciliation are complete, but T024 architecture acceptance
remains open because T022 physical evidence is unavailable. T025 is blocked by
that gate; no actual version, commit, tag, push or operational install occurred.

## Single-GPU estimation amendment (2026-10-27)

T022's exhaustive estimator count matrix is superseded by T031. Its separate physical
DDP and FCOS requirements remain unchanged. Previously completed tasks/evidence above
are historical checkpoints; the following tasks verify the changed implementation.

- [x] T027 Record inspected scope and validate the amended architecture plan.
- [x] T028 [P] Implement typed measured/extrapolated lookup, mixed-hardware compatibility, source provenance and null-batch regression tests.
- [x] T029 [P] Search once per distinct GPU type/capacity on the first idle selected GPU; make counts report-only and enforce one GPU per trial; test caching, refresh, ceilings and busy allocations.
- [x] T030 Update Russian README, maintained estimation/queue contracts, active feature documents and portable usage source; validate docs and examples.
- [ ] T031 Verify real single-GPU searches and derived reporting; run canonical and current/proposed paired queue checks and scoped mutation applicability. Physical DDP remains a separate T022 gate.
- [x] T032 Obtain fresh independent review after integration/checks, reconcile task-owned diff and architecture; evaluate release subject to remaining acceptance gates.

T027 precedes implementation; T028 and T029 have exclusive ownership. T030 follows
contract decisions. T031 follows integration, T032 follows verification. No bounded
agent delegates further. Python >=3.12.13,<3.14, uv and existing pinned dependencies
remain authoritative; no wheel/build/package publication or dependency changes.

T027–T030 and T032 are complete for the single-GPU amendment; see
[evidence](evidence/single-gpu.md). Current canonical/docs/paired checks and fresh
independent code review pass. T031 remains open for successful native YOLO fresh
confirmation: current attempts fail conservative GPU telemetry. FCOS single-GPU
search, cached reuse and refresh passed. T022's separate physical DDP gate remains
unavailable on a one-GPU host. Architecture acceptance therefore remains blocked,
as do T024/T025; no commit, version, tag, push or operational install was performed.

## Explicit release request (2026-10-27)

The later user request “make new release” follows the disclosed native gaps. It is
treated as authorization to deliver the reviewed implementation with those gaps
recorded, superseding the previous release stopping point for this delivery.
T022/T031 and full architecture acceptance remain open; missing checks are not passes.

- [x] T033 Reconcile release scope and documentation, preserve local uv sources, and prepare the compatible queue/usage companions.
- [x] T034 Run final canonical/docs checks with uv sources absent, verify final paired versions, and obtain fresh release review.
- [x] T035 Commit the feature through normal hooks, create the native semantic version/tag, publish verified companion and CY refs, and restore local uv sources.

T033 precedes T034. T035 requires successful ordinary checks and review; only the
disclosed native YOLO confirmation, broader FCOS/backend matrix and physical DDP
acceptance gaps are release exceptions.

## Search speedup amendment (2026-10-30)

- [x] T036 Record FR-013–FR-016/SC-006–SC-007 decisions and validate specs/006-batch-training/speedup/architecture.json before implementation.
- [x] T037 [P] [US1] Implement memory-guided search, strategy replay, schema-3 compatibility and regression tests in core/batch_estimation.py and tests/test_batch_search_strategy.py (FR-013, FR-014).
- [x] T038 [P] [US1] Implement independent process pool and real subprocess lifecycle tests in adapters/runtime/worker_pool.py and tests/test_worker_pool.py (FR-015, FR-016).
- [x] T039 [US1] Add case contracts, private entrypoint, idle hardware scheduling, jobs CLI and receipt/cancellation tests in application/training_workers.py and entrypoints/batch_estimate*.py (FR-015, FR-016).
- [x] T040 [US1] Extend architecture contracts/negative cases, catalogue multiprocess tests and integrated CLI/docs compatibility coverage in .importlinter and tests/ (FR-014–FR-016).
- [ ] T041 Record matching native one-GPU legacy/guided benchmarks in specs/006-batch-training/speedup/verification.md (SC-006); physical multi-GPU execution remains explicitly unverified (SC-007).
- [x] T042 Update docs/batch-estimation.md, README.md, active feature interfaces and portable usage source; validate Markdown, links, generated docs and examples (FR-013–FR-016).
- [x] T043 Run canonical verification, applicable mutation checks and latest/proposed paired CY/queue integration/static checks; record exact source identities and limitations in speedup evidence.
- [ ] T044 Obtain fresh independent review after integration/checks, resolve findings, reconcile task-owned diff and validate speedup architecture acceptance.
- [ ] T045 Complete the authorized new code release through normal commits/hooks, annotated tag and explicit verified pushes; preserve original dirty workspace and UV source overrides.

T036 precedes T037/T038; parent freezes case contracts before T039 integration.
T037 and T038 have exclusive write ownership. T040–T043 follow integration;
T044 follows parent verification, and T045 follows accepted review and release checks.
Historical tasks are not reopened or relabelled by this amendment.

T036–T040, T042 and T043 are complete; canonical verification passed 4,571 tests and
all static/import checks. Fresh independent review accepted the implementation with
no unresolved findings; see [review](speedup/review.md). T041 remains open after two
idle-preflight failures before native work. T044's design/diff reconciliation is done,
but full architecture acceptance remains open for that native check. T045 is pending
an idle-GPU benchmark or an explicit release exception for this separate gap. The
physical two-GPU exception alone does not waive the one-GPU comparison.

## Explicit delivery authorization, 2026-10-30

After disclosure of the two failed idle preflights and the separate single-GPU
benchmark gate, the user instructed **“push”**. This authorizes the Git-only 0.44.4
delivery with that benchmark gap recorded, in addition to the earlier physical
multi-GPU exception. It does not turn T041 or full architecture acceptance into
passes. Ordinary checks, independent review, final paired-source verification and
normal release hooks remain required; no native guarantee or idle criterion changes.

## Configurable queue admission follow-up (2026-10-30)

The later user request adds an optional queue admission threshold. Its implementation
belongs to cy-queue 0.1.6, with its own architecture, checks and fresh independent
review. CY's follow-up changes only portable guides, the baseline contract, the local
verification skill and the generated operations tutorial; its
[no-impact record](speedup/queue-docs-architecture.json) was validated before editing.

- [ ] T046 Reconcile CY queue guidance with the configured threshold, verify generated documentation and the final CY 0.44.4/queue 0.1.6 pair, and publish the reviewed companion sources with the authorized release.

No queue setting changes the estimator's separate idle/activity checks. The disclosed
native timing gap and its explicit delivery exception remain unchanged.
