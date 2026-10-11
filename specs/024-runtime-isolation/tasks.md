# Tasks: Controlled execution and library isolation

## Setup and foundation

- [x] T001 Capture approved requirements and ownership in specs/024-runtime-isolation/spec.md and plan.md.
- [x] T002 Inspect source/history/dependencies, preserve local overrides and create isolated implementation checkout.
- [x] T003 Analyze spec/plan/task consistency in specs/024-runtime-isolation/analysis.md before implementation.

## US2 — Queue and execution controls

- [x] T004 [P] [US2] Restore and test FIFO reservations/liveness in adapters/runtime/gpu_queue.py and gpu_runtime.py.
- [x] T005 [US2] Restore supervised execution, worker and Hydra launcher with bounded cancellation under entrypoints/hydra and hydra_plugins/cy_queue.
- [x] T006 [US2] Integrate four execution modes, replay identity checks and contraction in shared Hydra common/configs/validation and composition.py.

## US3 — Bounded FiftyOne

- [x] T007 [P] [US3] Add timeout fields and real subprocess adapter/worker tests in core/publication.py and adapters/fiftyone.
- [x] T008 [US3] Implement child-only configuration compatibility, finite locks and receipt/diagnostic validation in adapters/fiftyone.
- [x] T009 [US3] Integrate bounded publisher factory in entrypoints/composition.py and verify warning/cancellation behavior.

## US4 — Runtime isolation and cleanup

- [x] T010 [P] [US4] Implement stdlib pre-import runtime environment and scratch lifetime in adapters/runtime/bootstrap.py with tests/test_runtime_bootstrap.py.
- [x] T011 [US4] Reconcile storage/filesystem.py and thin entrypoints with project configuration and inherited worker environments.
- [x] T012 [US4] Verify temporary file cleanup, global configuration isolation, durable data retention and concurrent ownership through integration tests.

## US1 — Selected config export

- [x] T013 [P] [US1] Implement --command and exact output inventory in entrypoints/config_tree.py and entrypoints/hydra/config_tree.py with tests/test_config_tree.py.
- [x] T014 [US1] Update architecture/release composition tests and verify generated defaults include final execution/publication settings.

## Integration and verification

- [x] T015 Integrate combined changes and run pytest, Ruff, mypy, import-linter and distribution/installed-entrypoint checks.
- [x] T016 Run isolated native GPU concurrency and healthy/faulted FiftyOne acceptance; record evidence in verification.md.
- [x] T017 Obtain fresh independent review after parent verification and resolve findings.

## Documentation update (depends on implementation)

- [x] T018 Update README.md, docs/project-contracts.md, docs/current-contracts.md and docs/filesystem-policy.md.
- [x] T019 Update affected contracts, development/import/migration guidance and .agents/skills/running-end-to-end-tests guidance; preserve historical evidence.
- [x] T020 Validate changed Markdown/local links/examples and record results in verification.md.
- [x] T021 Follow docs/development.md commit/release procedure, preserve local uv sources, and publish only checked branch/version tags.

## Dependencies and parallel execution

T004/T007/T010 start in parallel after T003; parent works T006 interfaces. T005 follows
T004; T008 follows T007; T011 consumes T010; T009 consumes T007/T008. T013 can run when
a slot frees; T014 depends on final schemas. T012/T015 require integrated implementations.
Documentation runs alongside verification after interfaces settle. T017 follows parent
verification; T021 requires passing checks, documentation and fresh review.
