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
- [x] T025 Complete authorized commit and annotated-tag/push workflow only after acceptance; preserve local uv sources and dependency revisions (FR-011).
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
- [x] T041 Record matching native one-GPU legacy/guided benchmarks in specs/006-batch-training/speedup/verification.md (SC-006); physical multi-GPU execution remains explicitly unverified (SC-007).
- [x] T042 Update docs/batch-estimation.md, README.md, active feature interfaces and portable usage source; validate Markdown, links, generated docs and examples (FR-013–FR-016).
- [x] T043 Run canonical verification, applicable mutation checks and latest/proposed paired CY/queue integration/static checks; record exact source identities and limitations in speedup evidence.
- [x] T044 Obtain fresh independent review after integration/checks, resolve findings, reconcile task-owned diff and validate speedup architecture acceptance.
- [x] T045 Complete the authorized new code release through normal commits/hooks, annotated tag and explicit verified pushes; preserve original dirty workspace and UV source overrides.

T036 precedes T037/T038; parent freezes case contracts before T039 integration.
T037 and T038 have exclusive write ownership. T040–T043 follow integration;
T044 follows parent verification, and T045 follows accepted review and release checks.
Historical tasks are not reopened or relabelled by this amendment.

T036–T040, T042 and T043 are complete; canonical verification passed 4,571 tests and
all static/import checks. Fresh independent review accepted the implementation with
no unresolved findings; see [review](speedup/review.md). T041 remains open after two
idle-preflight failures before native work. T044's design/diff reconciliation is done,
but full architecture acceptance remains open for that native check. At this
pre-authorization checkpoint, T045 awaited an idle-GPU benchmark or an explicit
release exception for this separate gap. The
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

- [x] T046 Reconcile CY queue guidance with the configured threshold, verify generated documentation and the final CY 0.44.4/queue 0.1.6 pair, and publish the reviewed companion sources with the authorized release.

No queue setting changes the estimator's separate idle/activity checks. The disclosed
native timing gap and its explicit delivery exception remain unchanged.

T045 and T046 are complete: normal hooks, final canonical and paired checks passed;
CY 0.44.4, queue 0.1.6 and companion collection 0.6.7 were pushed with exact remote
ref verification. See [publication evidence](speedup/verification.md#verified-publication-2026-10-30)
and [companion refs](speedup/portable.md#verified-publication).


## Aligned automatic search follow-up (2026-11-02)

- [x] T047 Assess the eight-image per-GPU policy, historical replay and affected contracts; record docs/bugs/batch-align-eight/assessment.md and architecture.json.
- [x] T048 Add failing regression, implement versioned aligned search and automatic lookup filtering, and reconcile affected batch fixtures.
- [x] T049 Update and validate CY and portable usage documentation; complete focused, canonical and latest/proposed paired checks.
- [x] T050 Obtain fresh independent review, accept the reconciled architecture record, and complete the authorized patch release through hooks and verified Git pushes.

T047 precedes T048; T049 follows integration; T050 requires passing checks and review.
Historical performance/DDP limitations and delivery exceptions remain unchanged.


T047–T050 are complete. The aligned-policy regression and 461 focused batch cases
pass; canonical verification accepted 4,701 ordinary passes and all static/import
checks. Fresh independent review returned ship and architecture acceptance passed.
Final actual CY 0.44.7/queue 0.1.7 pairing passed 582 queue cases after normal
resolution and source/installed consistency checks. The annotated CY version tag,
queue test companion and portable collection 0.6.9 were pushed with exact remote
ref verification. See [dated evidence](../../docs/bugs/batch-align-eight/test.md).
Historical native timing/DDP limitations remain unchanged.


## Saved coverage listing (2026-11-03)

- [x] T051 Specify saved-coverage listing, architecture/effect ownership and dependency-ordered implementation; analyze consistency without rewriting historical acceptance.
- [x] T052 Add failing pure coverage and read-only CLI tests, implement report classification/rendering and conditional argument validation.
- [x] T053 Update README, batch contract, shared/help/generated documentation and portable usage skill; validate examples, metadata, links and discovery.
- [x] T054 Run focused and canonical verification, documentation validation and latest/proposed CY/queue compatibility checks.
- [x] T055 Obtain fresh independent review, reconcile task diff/architecture and checks, then release to master using normal hooks and verified Git-only pushes.

T051 precedes T052. T053 portable work may run independently; final generated docs
follow CLI changes. T054 requires T052/T053; T055 requires all acceptance evidence.
Prior native timing and physical-DDP limitations remain historical and unchanged.


T051–T055 are complete. The stable copied-environment canonical gate passed
4,735 ordinary cases and all static/import checks; fresh post-verification review
returned ship. Native hooks created and published annotated v0.45.0. The actual
CY0.45.0/queue0.1.8 pair passed normal installation, source/installed identity and
583 queue cases. Queue main and portable collection v0.7.2 were published with
exact ref verification. See [release evidence](list/verification.md). Existing
native timing and physical-DDP limitations remain historical and unchanged.


## Forced admission follow-up (2026-11-03)

- [x] T056 Record force requirements, architecture, source isolation and current dependency pair.
- [x] T057 Add regressions and implement force admission, persisted policy and visible source limitations; preserve strict defaults and foreign-workload protection.
- [ ] T058 Run the requested native catalogue and canonical checks; report actual failures without inventing capacity.
- [ ] T059 Reconcile README, maintained contracts and portable usage; validate docs and actual proposed-version CY/queue pairing.
- [ ] T060 Obtain fresh independent review, reconcile architecture and complete Git-only release when all applicable verification gates pass.

T056 precedes T057; T058/T059 follow implementation; T060 requires their evidence and review. Historical failed/unavailable physical gates remain recorded.

### Current-source reconciliation (2026-11-04)

The preserved force branch used T051–T055 before the independently delivered saved
listing occupied those IDs. This integration retains the delivered listing history
and maps only the unpublished force tasks to T056–T060. The original branch and
its dated evidence remain preserved. Runtime changes were ported onto CY 0.45.0;
the listing remains inert and explicitly rejects `--force`. The combined help
fixture retains `--list` and its conditional `--imgsz` requirement. Focused checks
are recorded in [the reconciliation evidence](force/reconciliation-2026-11-04.md).
Historical proposed CY 0.44.9/queue 0.1.7 results do not establish acceptance for
this current integration or its eventual release versions.

### Sequential integration continuation (2026-11-05)

DINOv3 and scoped campaign source precede this force port; preserve completed
T001–T057 history. Current integrated runtime evidence is separate from historical
pilot source/version results. No intermediate release precedes final native gates.

- [x] T061 Reconcile and validate the current force architecture plan, reproduce a force regression before runtime port, and port only owned implementation/tests/docs.
- [x] T062 Run focused CPU force/list/cache/telemetry regressions, current lint/docs checks, and reconcile the exact force diff.
- [x] T063 Parent verifies final integrated canonical checks, compatible latest/proposed source metadata and normal CY/queue resolution.
- [ ] T064 Parent verifies all 64 final-source native models and raw optimizer receipts, with fresh selected DINOv3 L/X confirmation; failed/interrupted cases remain gaps.
- [ ] T065 Parent completes portable guidance, fresh integrated review and architecture acceptance, then normal Git-only delivery and final actual-version pair recheck.

T061 precedes T062; T063/T064 require the frozen final source/environment; T065
requires every acceptance gate. Physical multi-GPU limits remain disclosed.

### Delivery note (2026-11-06)

The local release hook published this integrated source as **CY 0.46.0**
(`60edd4b`, tag `v0.46.0`). It fired on the first master commit after the
consolidation, `8a1d5a9` from [feature 011](../011-simplify-hooks/verification.md).
The user then authorized pushing that release together with cy-queue 0.1.9.

T063 is satisfied by:
- the complete CY suite and static checks run by the hooks on `8a1d5a9`;
- the committed-pair check: normal install, `uv pip check`, matching metadata and
  584 queue tests (recorded in cy-queue `docs/plans/cy-046-compatibility/verification.md`).

**Still open, and published regardless:**
- **T064:** native 64-model forced catalogue and fresh DINOv3 L/X confirmation.
- **T065:** portable guidance, fresh integrated review of the force and DINOv3 changes,
  and force architecture acceptance. Its delivery and final pair recheck are done; the
  other parts remain open.

The release does not claim those gates. Complete them as post-release acceptance.

## Matched native search comparison, 2026-11-05

T041 is complete through the current explicit force path: two matched models and
three strategies, actual full native optimizer trials, fresh confirmation and
unchanged cached relaunch. Dated [benchmark evidence](speedup/verification.md)
retains original idle-preflight failures, the harness correction and raw timing
limitations. No idle-device, statistical speedup or physical multi-GPU claim is
made. T044 remains pending final record review and architecture validation.


T044 is complete: fresh independent native comparison review accepted the seven
retained cases and 43 optimizer receipts; parent architecture acceptance and current
documentation validation passed. Earlier failed idle-preflight receipts remain
historical evidence. Current full catalogue and physical DDP acceptance are separate.

## Ledger reconciliation (2026-11-07)

This note reconciles open boxes with existing evidence for WP0 of the
[remaining-work plan](../../docs/plans/remaining-work-20261106/plan.md). Earlier
dated sections stay unchanged; missing checks are not relabelled as passes.

- **T022:** physical multi-GPU DDP acceptance is **waived by user decision
  (2026-11-06)**; it will not be done here and is not passed. The box stays
  unticked. Its estimator-matrix part was already superseded by T031 (see the
  2026-10-27 amendment). The 16 T026 DDP scenarios stay unexecuted.
- **T024:** stays unticked. The review and ledger parts are done: the 006
  [architecture record](architecture.json) review is `accepted` (reviewer
  `release_final_review`), with prior reviews in
  [evidence/review.md](evidence/review.md) and the release review in
  [evidence/release.md](evidence/release.md). Architecture acceptance stays open
  until T031 and the record's failed `native` check close in WP1. T022 and the
  not-run `ddp-native` check are waived, not passed. The record's results stay as
  recorded.
- **T025:** ticked. Delivered as CY v0.41.0 through T033–T035 under the explicit
  release request of 2026-10-27, with its disclosed native exceptions. That
  release exception replaced the box's "only after acceptance" order: delivery
  preceded architecture acceptance, which stays open with T024.
- **T031:** stays **open for WP1**. Owner decision: the forced yolo11n
  confirmation in [speedup/verification.md](speedup/verification.md#completed-matched-native-comparison--2026-11-05)
  is not the strict-idle confirmation T031 asks for. WP1/T064 closes it.
- **T058 and T060:** superseded by T064 and T065, and left unticked because that
  work is still open. T060's release part is done (CY 0.46.0, see the delivery note).
- **T059:** the pair and README parts are done (`c16dbb1`, and the 0.46.0 committed
  pair in cy-queue `docs/plans/cy-046-compatibility/verification.md`). The
  portable-guide part moves to WP3/T065, so the box stays unticked.
- **Queue test count:** the proposed-version pair records 583 queue tests and the
  committed-version pair records 584 (both with 7 physical opt-ins deselected).
  They are separate runs; neither record is rewritten.

Documentation check for the [force record](force/architecture.json): on 2026-11-07,
`uv run --frozen --no-sync python scripts/check_docs.py --all` exited 0 with
"Checked 268 Markdown files; 0 issue(s)." The recorded `scripts/verify.py --docs`
command no longer exists in the repository, so the record now names the command
that was run.
This check covers CY Markdown only. The record's portable-guidance expectation
is not established by it; the corp-skills guide still predates `--force` and is
owned by WP3/T065. The record's `docs` check therefore stays `not-run`, with this
partial result in its reason; WP3/T065 revisits it.

### T065 portable guidance — 2026-11-07

The portable-guidance part of T065 is done: corp-skills v0.7.5 (`11b6866`) documents
CY 0.46.0 `--force`, its `forced/background-sensitive` label, the reader upgrade and
the DINOv3 HF guidance; see the
[force verification](force/verification.md#portable-usage-guide-release--2026-11-07).
T065 stays unticked for its review, architecture acceptance and delivery parts.
