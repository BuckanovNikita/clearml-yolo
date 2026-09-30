# Tasks: Native ClearML tracking

**Input**: [spec.md](spec.md), [plan.md](plan.md), design and publication contract.
**Tests**: Required by the approved plan and constitution. Capture original failure before changing relay behavior.

> **Current-contract note:** Checked tasks preserve completed implementation history. Current
> replay reads current-task configuration; comparison resolves source weights/thresholds and
> records source links without automatically fetching source General/Configuration Objects.
> References to compared-model configuration recovery in T010–T012/T015 reflect the original
> target. See [current contracts](../../docs/current-contracts.md).

## Phase 1: Setup and Specification

- [x] T001 Complete assessment intake/research/define/shape/decide in .specify/assessments/native-clearml-integration/ and clarified specification in specs/010-native-clearml-integration/spec.md.
- [x] T002 Complete research/design, reviewer quality checklist and cross-artifact analysis in specs/010-native-clearml-integration/.

## Phase 2: Foundation

- [x] T003 Confirm unchanged relay context/replay interfaces, exclusive write ownership and v0.10 publication baseline in src/clearml_yolo/native_ddp.py and src/clearml_yolo/clearml_session.py before implementation (FR-002, FR-011).

## Phase 3: User Story 1 — Live native training progress

**Goal**: completed native epochs publish while DDP training continues.
**Independent test**: hold training open after a written epoch and assert owner callback dispatch precedes completion.

- [x] T004 [P] [US1] Capture failing live-DDP observation and add partial-record, context identity, callback-failure, terminal deferral and cleanup regressions in tests/test_native_ddp.py (FR-001–FR-004, SC-001, SC-005).
- [x] T005 [P] [US1] Add native callback registration, native scalar names/epoch indices, task reuse, plots=false and setting-restoration coverage in tests/test_native_tracking_contract.py (FR-001, FR-002, FR-006).
- [x] T006 [US1] Implement copied-context owner consumer, .25-second polling, incremental exactly-once ordered non-final dispatch and error propagation in src/clearml_yolo/native_ddp.py (FR-001–FR-004).
- [x] T007 [US1] Implement stop/join/final drain, validate complete journal before deferred on_train_end, apply final trainer state and preserve existing caller interfaces in src/clearml_yolo/native_ddp.py (FR-003, FR-004).

## Phase 4: User Story 2 — Native best model

**Goal**: exactly one downloadable verified best Output Model, no duplicate checkpoint artifact.
**Independent test**: downloaded native checkpoint matches local bytes and loads; incomplete journal cannot call terminal publication.

- [x] T008 [US2] Review and run model association/upload/flush/hash/metadata failure and uniqueness regressions in tests/test_clearml_native.py; add missing behavior assertions only where needed (FR-005, SC-002).
- [x] T009 [US2] Integrate final journal validation with existing model barriers and training wiring in src/clearml_yolo/tasks/train.py and src/clearml_yolo/clearml_native.py; change production code only for demonstrated gaps (FR-004, FR-005).

## Phase 5: User Story 3 — Clean artifacts and configuration recovery

**Goal**: performance-only inventory and canonical configuration-backed replay/comparison.
**Independent test**: command inventories exclude all diagnostic/config copies and task replay works without original files or config artifacts.

- [x] T010 [P] [US3] Audit and strengthen command artifact-inventory tests in tests/test_publication_commands.py, including table deduplication, overrides/manifests/receipts exclusions and historical compatibility (FR-007, FR-008, FR-010, FR-011).
- [x] T011 [P] [US3] Audit and strengthen repeated/numbered YAML, train_data_overrides.json, remote configuration replay and missing-config tests in tests/test_config_upload_commands.py (FR-008, FR-009, SC-003, SC-004).
- [x] T012 [US3] Correct demonstrated inventory/recovery gaps in src/clearml_yolo/clearml_session.py and affected task/comparison adapters without blanket filename filters or changing feature 009 resolution (FR-007–FR-010).

## Phase 6: Integration and Evidence

- [x] T013 Update Russian README.md for live native telemetry, final-model barriers and performance-only artifact policy (FR-001, FR-005, FR-007–FR-009).
- [x] T014 Run pytest, Ruff, strict mypy and import-linter; record results and combined-diff review in specs/010-native-clearml-integration/verification.md (all FRs).
- [x] T015 Follow E2E/environment skills for real multi-epoch CPU/single-GPU and pipeline acceptance, query backend telemetry during execution, inspect artifacts/configurations, download/hash/load best model and test replay/comparison; record physical DDP pass or explicit limitation in specs/010-native-clearml-integration/verification.md (SC-001–SC-005).
- [x] T016 Run converge and resolve any uncovered requirements, then update evidence-backed task status in specs/010-native-clearml-integration/tasks.md and specs/010-native-clearml-integration/verification.md.

## Dependencies and Execution Order

T001–T003 gate product implementation. T004 precedes T006; T006 precedes T007. T005, T010 and T011 can proceed alongside relay work with exclusive test-file ownership. T008 may run independently; T009 depends on T007/T008. T012 follows T010/T011 evidence and root owns production corrections. T013–T016 follow integrated changes; real verification does not replace repository gates.

## Parallel Execution and Ownership

Relay agent owns native_ddp.py/test_native_ddp.py; tracking agent owns test_native_tracking_contract.py; publication agent owns test_publication_commands.py/test_config_upload_commands.py. Root owns shared wiring, model review, README and real evidence. Artifact agent owns assessment/feature artifacts; root owns feature.json and final task-status approval. No overlapping writes, commits or dependency changes.

## Implementation Strategy

Deliver and independently validate US1 first while other agents protect existing US2/US3 guarantees. Root integrates and reviews all results, then performs real backend acceptance and converge. Existing user authorization covers implementation; no additional approval or release is inferred.


## Phase 7: Convergence

- [x] T017 Validate all required nonterminal native event fields before dispatch in src/clearml_yolo/native_ddp.py, including epoch, losses/lr, epoch_time/metrics and sample save_dir as applicable; add failing missing/malformed-field regressions in tests/test_native_ddp.py proving corrupt complete records fail without final model publication, while preserving genuine native values and copied-context cleanup, per FR-001, FR-003, FR-004 and plan: record-shape validation (partial, HIGH).
