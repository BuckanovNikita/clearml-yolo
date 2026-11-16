# Tasks: Estimated-batch native acceptance

**Input**: [plan.md](plan.md), [spec.md](spec.md), research, model and contract artifacts.

## Phase 1: Setup

- [x] T001 Record approved scope and native specification quality checklist in `spec.md` and `checklists/requirements.md` (FR-001–008).
- [x] T002 Record research/design/contracts in `plan.md`, `research.md`, `data-model.md`, `contracts/acceptance.md` (FR-001–008).

## Phase 2: Foundations

- [x] T003 Add typed recipe/reserve transport and compatibility behavior in `src/clearml_yolo/application/training_workers.py` and `src/clearml_yolo/core/batch_estimation.py` (FR-001,006).

## Phase 3: US1 — Exact recipe measurements

- [x] T004 [US1] Red/green profile and worker recipe regressions in `tests/test_batch_profiles.py` and `tests/test_batch_probe.py` (FR-001,005).
- [x] T005 [US1] Carry recipe identity and settings in `src/clearml_yolo/adapters/integrations/batch_profiles.py` and `batch_probe.py` (FR-001).
- [x] T006 [US1] Execute custom augmentation with conservative bounds in existing backend probe modules and shared augmentation adapter; verify through product probe/dataset seams (FR-002).

## Phase 4: US3 — Memory admission

- [x] T007 [US3] Red/green optional reserve and cancellation regressions in `tests/test_batch_probe.py` and `tests/test_batch_estimation.py` (FR-005,006).
- [x] T008 [US3] Implement reserve enforcement at native worker admission/monitoring in `src/clearml_yolo/adapters/integrations/batch_probe.py` (FR-006,008).

## Phase 5: US2 — Two-epoch acceptance

- [x] T009 [US2] Test bounded usable-capacity selection through `src/clearml_yolo/core/batch_estimation.py` in `tests/test_batch_estimation.py` (FR-003,005).
- [x] T010 [US2] Update `tests/severstal_harness.py` to freshly measure, record admission and explicit batch, train two epochs, and optionally reuse a contained shared home with case-owned scratch and owned nested-process cleanup (FR-003–008).
- [x] T011 [US2] Reconcile maintained docs `docs/augmentation.md`, `docs/batch-estimation.md` and existing product composition expectations (FR-001–008).

## Phase 6: Acceptance and review

- [x] T012 Run focused product checks, typing/lint/architecture and scoped mutation review; record dated evidence under this feature (FR-001–006,008).
- [ ] T013 Run coordinator-admitted representative native GPU scenario through checkpoint reload and publication readback; record timing and cleanup (FR-007,008).
- [ ] T014 Obtain independent review after integration/checks, reconcile ticket03 and commit via coordinator (FR-001–008).

## Dependencies and execution order

T001→T002→T003; T004/T005 proceed in vertical red/green slices, then T006.
T007/T008 follow transport; T009/T010 require exact-recipe measurement and admission.
T011 precedes T012, then T013 and T014. No nested delegation; separate backend work
could be parallelized after shared contract integration, but this bounded owner is serial.

## Implementation strategy

Deliver exact-recipe measurement first, then reserve enforcement, then fresh acceptance
orchestration. Every implementation slice starts at the agreed public product seam.
Native execution/review remain explicit acceptance gates; no tooling-mirroring tests.
