# Tasks: Readable shared queue

## Phase 1: Setup and foundation

- [x] T001 Inspect current code/contracts and preserve existing changes; record approved intent in specs/034-readable-shared-queue/spec.md.
- [x] T002 Record and validate module contracts in specs/034-readable-shared-queue/architecture.json; analyze spec/plan/task coverage before code.

## Phase 2: Shared configuration (US3)

- [x] T003 [P] [US3] Add failing settings/propagation/namespace tests in tests/test_queue_settings.py.
- [x] T004 [P] [US3] Implement typed shared settings and binding in src/clearml_yolo/adapters/queue/settings.py and coordination.py, with runtime/guardian propagation.
- [x] T005 [US3] Integrate mandatory settings and read-only config output in src/clearml_yolo/entrypoints/queue.py.

## Phase 3: Readable output (US1)

- [x] T006 [P] [US1] Add failing display, stream-boundary and report-provenance tests in tests/test_readable_output.py and affected console/identity tests.
- [x] T007 [P] [US1] Implement pure human formatting and report/console boundaries in src/clearml_yolo/core/presentation.py and reporting/observability/ClearML adapters.
- [x] T008 [US1] Implement readable defaults, explicit JSON, references, labels and selection in src/clearml_yolo/entrypoints/queue.py, queue_presentation.py, queue_tui.py and hydra/queue_config.py.
- [x] T009 [US1] Replace hash GPU fallback labels and visible sweep tags in src/clearml_yolo/core/gpu_identity.py and entrypoints/hydra/sweeps.py with readable aliases; retain machine selector compatibility.

## Phase 4: Archive (US2)

- [x] T010 [P] [US2] Add failing archive/reference/ownership/replay tests in tests/test_queue_archive.py.
- [x] T011 [P] [US2] Implement atomic archive and reference/view policy in src/clearml_yolo/core/queue.py, application/queue.py and adapters/queue/storage.py.
- [x] T012 [US2] Integrate archive/restore and visibility in src/clearml_yolo/entrypoints/queue.py and queue_tui.py.

## Phase 5: Integration and acceptance

- [x] T013 Confirm existing exhaustive pyproject.toml module contracts and add negative boundaries in tests/test_architecture.py (no rule widening).
- [x] T014 Implement reusable real two-user harness in tests/queue_multiuser_harness.py; provision, execute and clean up isolated temporary users; retain evidence in specs/034-readable-shared-queue/verification.md.
- [x] T015 Run scoped then full behavior/static/architecture and native publication checks, retaining results in specs/034-readable-shared-queue/verification.md.

## Phase 6: Documentation, review and delivery

- [x] T016 Update README.md, docs/queue.md, docs/filesystem-policy.md, docs/diagnostics.md, docs/current-contracts.md and affected identity/publication contracts.
- [x] T017 Update canonical corp-skills/skills/clearml-yolo/SKILL.md and references/usage.md and references/evaluation.md; validate package/docs/examples.
- [x] T018 Validate Markdown, local links and examples; reconcile architecture/diff/evidence and obtain fresh independent review in specs/034-readable-shared-queue/review.md.
- [ ] T019 Validate architecture acceptance and deliver task-scoped commits/native Git-tag-only release per docs/development.md, preserving local source overrides and unrelated files.

## Dependencies and parallel ownership

T001/T002 precede all code. Settings, archive and report/console workstreams own disjoint
files and may run concurrently; the parent owns CLI/TUI and integrates their interfaces.
T004 coordinates the storage constructor with T011. T005/T008/T012 follow their respective
core/adapter contracts. T013-T017 follow integration; T018 follows executed checks and
documentation; T019 follows accepted review and architecture reconciliation.

## Integration findings

- Parent reproduced and corrected archived history reappearing in the response to a
  successful move; the application response now applies Main visibility after full replay.
- Real service readback found SDK startup announcements bypassing console capture and
  publishing raw task references. The bounded startup routing correction passed a fresh
  live CPU acceptance run; subsequent CPU and single-GPU publication checks also passed.
- Real two-user acceptance and injected-failure cleanup passed. See
  [multiuser evidence](multiuser-evidence.md); physical GPU observations were synthetic.
- Companion usage guidance is prepared in its source repository for version 0.2.7.
  Fresh-context evaluation and review passed after correcting the raw-log guidance;
  publication follows application delivery.
- Fresh runtime review reproduced a queue task-name interpolation failure. Parent added
  CLI and saved-configuration regressions, kept overrides unresolved until a job context
  exists, and derived display labels from frozen values. Mixed views now mark archived
  rows; duplicate legacy/readable references count as one archive target.
- Output review identified partial UTF-8 barrier liveness, punctuation-split identifier
  masking, opaque class-name rendering and no-argument brace formatting gaps. Corrections
  passed focused verification and independent rereview. A further collision finding led
  to distinct table aliases and invocation-owned scalar aliases stable across updates.
  Final parent checks passed 439 affected tests, strict typing, lint and import contracts;
  fresh active live readback passed. Final independent rereview accepted the result
  after 117 tests and 24 alias arrival orders. The complete routine suite passed
  2,927 tests; commit and release hooks execute their required gates separately.
