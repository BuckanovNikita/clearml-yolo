# Tasks: direct execution and shared cy-queue

## Foundation

- [x] T001 Inspect implementation, existing edits, constitution and current contracts; preserve v0.26.1 history in specs/029-shared-cy-queue/plan.md.
- [x] T002 Specify requirements, module interfaces and architecture.json; validate architecture planning before implementation.
- [x] T003 [P] Capture frozen-source eager/compiled baseline and isolated CPU-DDP SIGILL investigation in baseline-2026-10-13.md.

## US1: direct execution and project storage

- [x] T004 [US1] Add failing direct/import/config/path tests in tests/test_direct_execution.py, tests/test_runtime_bootstrap.py and tests/test_filesystem.py.
- [x] T005 [US1] Remove queue/autogpu routing/imports and default plugin from entrypoints/hydra, composition, runtime/bootstrap and packaging; reject legacy controls with migration guidance.
- [x] T006 [US1] Enforce project-contained application destinations before all writes in adapters/storage and Hydra setup; preserve SDK/input paths.

## US2: queue policy, persistence and supervision

- [x] T007 [P] [US2] Add pure request/order/allocation tests and implement core/queue.py and application/queue.py with explicit ports.
- [x] T008 [P] [US2] Test and implement adapters/queue storage, host-global locks, UID/private/public ownership, revisions, atomic manifests/order events and fail-closed corruption/NFS handling.
- [x] T009 [P] [US2] Test and implement guardians, worker concurrency, cancellation and owner recovery; integrate runtime/process_tree protections including repeated signals and worker/guardian forced death.
- [x] T010 [US2] Implement queue CLI/snapshot composition/execution and optional TUI after application interfaces; expand whole sweeps before submit and validate compatibility/bindings.
- [ ] T011 [US2] Verify actual multi-user, NFS and host partition acceptance; record unavailable infrastructure explicitly.

## US3: logs, progress and native evidence

- [x] T012 [P] [US3] Add failing FD/child/partial-line capture, publisher failure/shutdown and error preservation tests; implement observability capture and attach-only ClearML publisher.
- [x] T013 [P] [US3] Preserve live DDP/other-backend scalars and bound relay shutdown; independently verify remote console/scalars during active training.
- [x] T014 [P] [US3] Implement quiet prediction and one rate-limited operation progress across YOLO/native/comparison backends with image/numerical parity and failure closure tests.
- [ ] T015 [US3] Compare direct/queued single/five-GPU eager/compiled execution, physical cancellation, forced termination and filesystem write audit; preserve unresolved native failures.

## Integration, documentation and acceptance

- [x] T016 Extend pyproject/import graph and tests/test_architecture.py negative cases for direct/queue/SDK/dynamic targets; reconcile complete diff with architecture.json.
- [x] T017 Update Russian README, docs/project-contracts.md, current-contracts.md, filesystem-policy.md, runtime-isolation.md, diagnostics.md, development.md, examples and Ctrl+C task records.
- [x] T018 Run full pytest/Ruff/mypy/Vulture/import-linter/architecture, Markdown/local links/examples and fresh installed wheel/sdist verification; record exact results in verification.md.
- [ ] T019 Obtain fresh independent read-only review after parent integration/checks; fix findings and validate architecture acceptance.
- [ ] T020 Complete documented task-scoped commit and Git-tag-only release after all required gates pass; restore exact local tool.uv.sources unstaged.

## Dependencies and ownership

T001-T002 precede production edits. T003 runs from frozen sources independently.
Parent owns T004-T006, T010 and T016-T020. Queue implementer owns T007-T009 with
exclusive core/queue.py, application/queue.py, adapters/queue and tests/test_shared_queue*.
Observability implementer owns T012-T014 and its capture/publisher/progress/native files/tests.
T010 depends on T007 interfaces; T015 depends on integrated execution. T018 precedes
T019, and T019 precedes T020. Unavailable target acceptance keeps tasks open.

## Review and native amendments

- [x] T021 Resolve effective Hydra mode, saved sweep parameters, strict top-level pipeline
  inputs and saved legacy migration findings; refresh regression, distribution and independent
  review evidence for the new shared composition module before T020.
- [x] T022 Investigate the actual post-upload ClearML Task.close timeout without assuming
  descendant cleanup caused it; retain PID/trace evidence and distinguish passing diagnostics
  from a root-cause fix. Complete all available native phases and record unresolved acceptance.

- [x] T023 Reproduce transient `/proc` denial during native rank exit in the retained
  supervision release path; retry verification only within its existing cleanup deadline,
  preserve permanent-denial fail-closed behavior, and refresh native/process/full acceptance.

- [x] T024 Reproduce and close the fourth execution review's native-output ZIP leaf
  symlink escape; verify real ZIP content/parity and external-sentinel preservation,
  refresh software gates and obtain fresh execution review. Preserve the native
  matrix's frozen source identity and record this later containment-only correction.

- [x] T025 Prevent a sequential Hydra invocation from reusing an incompletely
  finalized ClearML owner. Reproduce the retained SDK singleton path, block later
  task creation/workflow effects without resetting SDK internals or replacing the
  original error, and verify normal closed invocations remain sequentially usable.

- [x] T026 Preserve graceful owner shutdown during normal queue cancellation:
  signal the verified native owner first, retain the full allocation through a
  bounded grace period, then apply existing verified whole-tree cleanup. Reproduce
  publisher/child premature termination, verify deadline escalation and repeated
  signals, and rerun actual cancellation with independent remote-log readback.

- [x] T027 Stop the invocation-owned ClearML development status monitor before
  reporting failure when normal close cannot run. Preserve singleton quarantine,
  original exceptions, bounded teardown and required failed status; retain and
  rerun actual publisher SIGSTOP/SIGKILL fault evidence. Do not change SDK policy
  or another task's monitor, and do not retry an interrupted close at process exit.

## Phase 1: Convergence

- [ ] T028 Complete the unavailable five-physical-GPU and actual two-user/two-host
  NFS acceptance when a target exists, preserving unresolved cuBLAS/SIGILL evidence
  and the user-confirmed infrastructure gap; reconcile T011/T015 per success
  criteria, US2 acceptance and FR-18 (partial, HIGH).
- [x] T029 Replay actual publisher SIGSTOP/SIGKILL with original computation failure,
  normal queue cancellation and sequential ClearML ownership on the corrected
  immutable source; retain independent terminal-status/console evidence and reconcile
  T022/T025-T027 per FR-11, FR-15, FR-16 and US3 acceptance (partial, HIGH).
- [x] T030 Finish final-source software/distribution/documentation gates and fresh
  independent review, reconcile architecture acceptance and keep release blocked
  while required target gates remain open; reconcile T018-T020/T024 per success
  criteria and plan verification/release dependencies (partial, HIGH).
- [x] T031 Align the data-model transition document's `succeeded` label with the
  implemented `completed` state and validate its links per plan data-model contract
  and FR-09/FR-11 (partial, LOW).

- [x] T032 Preserve the original computation/publication exception when a secondary
  cleanup diagnostic sink raises. Reproduce the fifth review's real Loguru
  `catch=False` failure, guard barrier/finalization/console diagnostics, verify
  terminal cleanup still runs, and renew final execution review per FR-16.

- [x] T033 Preserve the original direct-execution failure when GPU memory cleanup
  raises an ordinary exception or interruption and its diagnostic sink also fails.
  Reproduce the sixth review, share protected cleanup diagnostic emission through
  the observability adapter, preserve propagation when no primary error exists,
  renew verification and fresh execution review per FR-16.

## Final available-environment outcome — 2026-10-13

Implementation, all available software/native checks, documentation and fresh
independent software reviews are complete. T019's review portion passed; its full
architecture acceptance remains blocked by the unavailable native check. T011,
T015 and T028 retain actual two-user/two-host NFS and five-physical-GPU acceptance.
The user confirmed no additional environment is available. Original cuBLAS and
intermittent SIGILL investigations, plus reproduced SDK missing-model-ID failure,
remain unresolved rather than being declared fixed by passing runs.

T030 closes final evidence reconciliation, not the unavailable gates. T020 remains
blocked: no commit, version tag, push or package publication was performed. Exact
local dependency source overrides and prior completed history remain intact.

## User-directed release continuation — 2026-10-13

After the available-environment outcome above was reported, the user explicitly
requested “make release”. This authorizes the Git-tag-only release with the already
disclosed limitations; it does not supply missing target evidence or resolve native
failures. T011, T015, T028 and the native portion of T019 remain open. The preceding
release deferral remains historical evidence, superseded by this explicit request.

- [ ] T034 Reconcile published v0.26.2 cancellation history, run normal commit/release
  hooks, verify release metadata and installed distributions, obtain independent
  release review, and publish the checked branch and annotated Git tag. Record
  exact refs and limitations in [release evidence](release-2026-10-13.md).

- [x] T035 Restore shipped v0.26.2 process-tree safeguards discovered by release
  audit: marker-only supervised ownership, refreshed birth/liveness evidence and
  two stable empty scans. Reproduce with the original upstream tests, preserve the
  refactor's direct/subreaper behavior, renew focused/full checks and fresh review.
