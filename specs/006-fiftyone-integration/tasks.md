# Tasks: FiftyOne Integration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [publisher contract](contracts/publisher.md)

## Phase 1: Setup

- [x] T001 Add FiftyOne main dependency and import-linter package boundary in pyproject.toml
- [x] T002 [P] Add default FiftyOne config registration only for pipeline, predict, and metrics in src/clearml_yolo/configs.py
- [x] T003 [P] Add config/default behavior tests in tests/test_publishing.py

## Phase 2: Foundational

- [x] T004 Create neutral publisher models, protocol, config factory, and no-op implementation in src/clearml_yolo/publishing/
- [x] T005 Create local dataset lock, identity validation, completion-marker, and receipt helpers in src/clearml_yolo/publishing/
- [x] T006 [P] Create no-op/import-isolation, identity/path-conflict, retry, and lock tests in tests/test_publishing.py and tests/test_fiftyone_publisher.py
- [x] T007 Add local/ClearML receipt artifact naming helpers in src/clearml_yolo/artifact_names.py

## Phase 3: User Story 1 - Review an eligible run (Priority: P1) 🎯 MVP

**Goal**: Publish eligible results once with one sample per source image and no media copy/UI.

**Independent Test**: Fixture publication contains required metadata/backgrounds and one owner receipt.

- [x] T008 [P] [US1] Create the sole FiftyOne adapter and media-reference sample mapping in src/clearml_yolo/publishing/fiftyone_adapter.py
- [x] T009 [P] [US1] Add adapter sample/background/raw-prediction tests in tests/test_fiftyone_publisher.py
- [x] T010 [US1] Integrate publication preflight and standalone prediction owner receipt in src/clearml_yolo/tasks/predict.py
- [x] T011 [US1] Integrate pipeline single-owner publishing and nested disable switch in src/clearml_yolo/tasks/pipeline.py
- [x] T012 [US1] Add eligible-command/single-owner strict-failure tests in tests/test_pipeline.py and tests/test_predict.py

## Phase 4: User Story 2 - Reuse a completed import safely (Priority: P2)

**Goal**: Reuse only compatible completed data and repair only the retrying task scope.

**Independent Test**: Completed matching import reuses; changed resolved path fails; concurrent/retry fixtures preserve other task fields.

- [x] T013 [US2] Implement dataset reuse, resolved-path revalidation, and task-scoped recovery in src/clearml_yolo/publishing/fiftyone_adapter.py
- [x] T014 [US2] Add reuse, conflict, idempotency, retry, and concurrency tests in tests/test_fiftyone_publisher.py
- [x] T015 [US2] Record and upload exactly one owner receipt in src/clearml_yolo/tasks/predict.py, src/clearml_yolo/tasks/metrics.py, and src/clearml_yolo/tasks/pipeline.py

## Phase 5: User Story 3 - Inspect exact evaluated outcomes (Priority: P3)

**Goal**: Persist and publish exact fixed-threshold evaluation payloads without rematching.

**Independent Test**: Fixture payloads and adapter annotations agree on index, label, TP/FP/FN/filtered status, confidence, and IoU.

- [x] T016 [US3] Create schema-versioned Pydantic evaluation payload models in src/clearml_yolo/comparison/evaluation_payload.py
- [x] T017 [US3] Export exact fixed-threshold scoring payloads without rematching in src/clearml_yolo/comparison/scoring.py
- [x] T018 [US3] Persist payload paths through MetricsResult and metrics output in src/clearml_yolo/tasks/metrics.py
- [x] T019 [US3] Integrate metrics owner publication and nested disable parameter in src/clearml_yolo/tasks/metrics.py
- [x] T020 [P] [US3] Add payload/fidelity/normalization/empty/background tests in tests/test_evaluation_payload.py and tests/test_metrics.py
- [x] T021 [US3] Add adapter evaluated-vs-raw field and matching-fidelity tests in tests/test_fiftyone_publisher.py

## Phase 6: Polish and Evidence

- [x] T022 Document supported config defaults in specs/006-fiftyone-integration/quickstart.md without modifying parent-owned README.md
- [x] T023 Run full static and unit gates recorded in specs/006-fiftyone-integration/quickstart.md
- [x] T024 Run and record a real FiftyOne persistent-DB smoke under task-owned output evidence
- [x] T025 Run and record real pipeline evidence using the running-end-to-end-tests workflow

## Dependencies & Execution Order

T001–T007 block stories. US1 needs T004–T007; US2 follows adapter creation; US3 needs the foundational publisher and its payload tasks. Pipeline integration follows standalone owner paths. T023–T025 follow all implementation.

## Parallel Opportunities

T002/T003, T005/T006, T008/T009, and T020 can run alongside independent file work. The scoring/payload tasks T016–T018 are intentionally isolated from publisher adapter work.

## Implementation Strategy

Deliver T001–T012 first for an inspectable eligible run, then reuse/recovery, then exact evaluated payloads. Do not claim external evidence until T024–T025 complete.

## Phase 7: Convergence

- [x] T026 Hash and parse the same GT CSV byte snapshot, with concurrent-update regression coverage, per FR-005/FR-006 (partial).
- [x] T027 Include dataset/run completion flags, payload paths, and an aware publication timestamp in receipts with real-backend round-trip coverage, per data-model: PublicationReceipt and FR-014 (partial).
