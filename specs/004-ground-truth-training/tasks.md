# Tasks: Ground-Truth-Driven Training

**Input**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), and contracts.

**Tests**: Required by the accepted workflow; write failing behavior tests before code.

## Phase 1: Setup

- [X] T001 Inspect existing contracts, clarify accepted corrections, and establish the baseline in `specs/004-ground-truth-training/plan.md`.
- [X] T002 Complete parallel research, requirements review, and cross-artifact analysis in `specs/004-ground-truth-training/research.md` and `checklists/dataset-contract.md`.
- [X] T003 Declare direct image dependency and dataset import layers in `pyproject.toml` and update `uv.lock` without changing external dependency revisions.

## Phase 2: Foundational Records

- [X] T004 Write failing validation/cleaning tests in `tests/test_dataset_records.py` for CSV schema, paths, backgrounds, invalid boxes, exact error counts, duplicate identity, split isolation, and deterministic classes (FR-002–FR-006, FR-019; SC-002–SC-004).
- [X] T005 Implement `src/clearml_yolo/dataset_records.py` typed records and validation; pixel dimensions are positive integers, splits are train/val/test, invalid boxes are dropped once, and at least one valid training box must survive (FR-002–FR-006, FR-019).

## Phase 3: User Story 1 — CSV Training (P1)

**Goal**: Complete standalone and full-pipeline training from CSV, with cleaned evaluation.
**Independent test**: CSV plus images produces a checkpoint and requested evaluation outputs.

- [X] T006 [P] [US1] Write failing preparation/policy tests in `tests/test_dataset.py` for fresh output reservation, cleaned CSV, manifests, defaults, invalid-box logging, and source preservation (FR-001, FR-010–FR-014, FR-019).
- [X] T007 [P] [US1] Write failing task/config integration tests in `tests/test_train.py`, `tests/test_pipeline.py`, and `tests/test_configs.py` (FR-001, FR-007, FR-011, FR-012, FR-016, FR-017; SC-001, SC-006).
- [X] T008 [US1] Implement preparation and data-policy functions in `src/clearml_yolo/dataset.py`, consuming canonical records and exporters (FR-001, FR-010–FR-014, FR-019).
- [X] T009 [US1] Integrate CSV preparation and cleaned output into `src/clearml_yolo/tasks/train.py` and `src/clearml_yolo/tasks/pipeline.py`; expose defaults in `src/clearml_yolo/configs.py` (FR-001, FR-007, FR-011, FR-012, FR-016, FR-017).

## Phase 4: User Story 2 — Both Representations (P1)

**Goal**: NDJSON and flat export preserve equivalent valid data.
**Independent test**: Inspect both exports and consume them with the installed native loader.

- [X] T010 [P] [US2] Write failing format-fidelity/native-consumption tests in `tests/test_dataset_export.py`, including local images, backgrounds, stem collisions, and 0.01-pixel tolerance (FR-008–FR-010; SC-002, SC-003).
- [X] T011 [US2] Implement both export modes in `src/clearml_yolo/dataset_export.py`, with isolated local images and native conversion byproducts (FR-008–FR-010, FR-013).

## Phase 5: User Story 3 — Ownership and Diagnostics (P2)

**Goal**: Dataset overrides and failure outcomes are inspectable without leaking images.
**Independent test**: Conflicting settings resolve to CSV ownership and required failures retain diagnostics.

- [X] T012 [US3] Verify preparation artifacts, data overrides, no image uploads, resume rejection, and failure propagation in `tests/test_train.py`, `tests/test_pipeline.py`, and `tests/test_dataset.py`; finalize task integration (FR-011–FR-015, FR-019; SC-004, SC-006).
- [X] T013 [P] [US3] Update `src/clearml_yolo/config_tree.py`, `tests/test_config_tree.py`, and `README.md` with NDJSON/flat examples, invalid-box reporting, and legacy native-data compatibility (FR-007, FR-017, FR-018).

## Phase 6: Verification and Convergence

- [X] T014 Run repository gates and record outcomes in `specs/004-ground-truth-training/verification-2026-09-29.md` (FR-001–FR-019; SC-001–SC-006).
- [X] T015 Execute real standalone and pipeline runs for NDJSON and flat, paired comparison, artifact downloads, and required failure checks; record portable evidence in `specs/004-ground-truth-training/verification-2026-09-29.md` (FR-013–FR-017, FR-019; SC-001, SC-005, SC-006).
- [X] T016 Run `$speckit-converge` against `specs/004-ground-truth-training/spec.md`, `plan.md`, and this `tasks.md`; append any remaining tasks and complete them with verification.
- [X] T017 Inspect the complete diff, rerun required checks, obtain fresh independent read-only subagent review, and record the verdict in `specs/004-ground-truth-training/verification-2026-09-29.md`.

## Dependencies and Parallel Ownership

T001–T003 precede implementation. T004 precedes T005. Once canonical interfaces are fixed,
T006/T007/T010 may run in parallel with disjoint tests; T008 depends on T005 and T011 for
execution, while task integration can be written against its settled interface. T010/T011
are the prerequisite exporter slice for T008/T009, despite their story grouping here.
T012 shares task files with T009 and runs sequentially under the same owner. T013 is
independent once public settings are settled. T014/T015 follow integrated code. T016 follows
implementation and evidence, and T017 follows convergence and final checks.

Record owner: `dataset_records.py` and `test_dataset_records.py`. Export owner:
`dataset_export.py` and `test_dataset_export.py`. Task owner: train/pipeline/configs and
corresponding tests. Parent: dataset orchestration/policy, dependency/import configuration,
examples/documentation, evidence, and acceptance. Owners do not mark each other's tasks.

## Implementation Strategy

Deliver and test canonical records first, then integrate both native representations and
CSV task flow. Both formats ship together. Follow the parallel routing and remaining
Spec Kit lifecycle in [workflow-plan.md](workflow-plan.md). No commit or push is included.

## Phase 7: Convergence

- [X] T018 Add an explicit same-stem filename and pixel-coordinate round-trip regression for both exports in `tests/test_dataset_export.py` per FR-009, FR-010, SC-002 and T010 (partial verification coverage).
