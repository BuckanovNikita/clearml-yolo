# Tasks: Native Ultralytics configuration groups

**Input**: [spec.md](spec.md), [plan.md](plan.md), research, data model and contracts.

Tasks are unchecked until implementation or executed evidence supports completion. Heavy tests
were authorized explicitly on 2026-09-28 and completed successfully. The user subsequently authorized committing and pushing to master.

## Phase 1: Setup

- [x] T001 Specify and clarify approved behavior in specs/003-ultralytics-config-groups/spec.md.
- [x] T002 Amend .specify/memory/constitution.md to 4.0.0 for the incompatible groups contract.
- [x] T003 Generate design artifacts and requirements checklist in specs/003-ultralytics-config-groups/.

## Phase 2: Foundation

- [x] T004 Add directly declared comment-preserving YAML support in pyproject.toml and uv.lock without changing external dependency revisions (FR-012).
- [x] T005 Implement runtime-free upstream template loading, full-key stage classification and comment-preserving serialization in src/clearml_yolo/native_config.py (FR-002, FR-005).
- [x] T006 Test native key/comment coverage and train internal-validation applicability in tests/test_native_config.py (SC-002).

## Phase 3: US1 - Paste native configuration

Independent acceptance: all model command examples compose with unchanged upstream YAML and
ordinary native overrides, without model runtime imports or ClearML creation.

- [x] T007 [US1] Replace raw-file overlays with shared/prediction Hydra groups in src/clearml_yolo/configs.py (FR-003, FR-007).
- [x] T008 [US1] Generate command examples plus two commented native files with complete collision checks in src/clearml_yolo/config_tree.py (FR-001, FR-011).
- [x] T009 [US1] Cover group selection, pasted upstream YAML, CLI overrides and removed interfaces in tests/test_configs.py and tests/test_config_tree.py (SC-001, SC-004).

## Phase 4: US2 - Override prediction settings

Independent acceptance: captured native arguments preserve shared inheritance and explicit
prediction values, enforce owned inputs, and match between comparison roles.

- [x] T010 [US2] Integrate explicit prediction precedence, null/default handling and batch validation in src/clearml_yolo/native_config.py (FR-004).
- [x] T011 [US2] Resolve stage-native inputs and reject conflicting model/output selections in src/clearml_yolo/tasks/train.py, src/clearml_yolo/tasks/predict.py and src/clearml_yolo/tasks/pipeline.py (FR-005, FR-006).
- [x] T012 [US2] Use the shared contract in src/clearml_yolo/tasks/val.py and src/clearml_yolo/comparison/ while retaining comparison-only controls (FR-003, FR-006, FR-007).
- [x] T013 [US2] Test explicit null/default precedence, AutoBatch rejection, checkpoint routing and paired comparison settings in tests/ (SC-003, SC-004).

## Phase 5: US3 - Inspect and replay native settings

Independent acceptance: active exported YAML matches captured native arguments and retained
sources; mocked ClearML configuration/artifact records retain comments and failure semantics.

- [x] T014 [US3] Retain source manifests and emit effective stage/split/role YAML in src/clearml_yolo/inference.py and src/clearml_yolo/tasks/ (FR-008, FR-009).
- [x] T015 [US3] Connect sanitized commented native YAML and upload required artifacts through src/clearml_yolo/clearml_session.py and existing task boundaries (FR-010, FR-011).
- [x] T016 [US3] Test native YAML parsing, manifest retention, publication identities, sanitization, upload/flush failure and one-task ownership in tests/ (SC-003, SC-004).

## Phase 6: Polish and convergence

- [x] T017 [P] Update README.md, AGENTS.md, docs/migration-ultralytics-groups.md and current specs/001-release-030/contracts/ to the new interface.
- [x] T018 Review requirement/task coverage and constitution consistency using specs/003-ultralytics-config-groups/spec.md, plan.md and tasks.md before implementation completion.
- [x] T019 Run focused lightweight pytest, Ruff, mypy, import-linter and documentation checks; record actual commands and limitations in specs/003-ultralytics-config-groups/verification-2026-09-28.md.
- [x] T020 Converge implementation against specs/003-ultralytics-config-groups/spec.md; append remaining gaps to this task list rather than declaring unverified outcomes complete.
- [x] T021 Authorized by the user on 2026-09-28: follow running-end-to-end-tests for real native training/prediction/comparison, ClearML download and native YAML replay; record dated evidence under specs/003-ultralytics-config-groups/ (SC-005, FR-012).

## Dependencies and parallel execution

T001–T003 establish intent. T004–T006 establish the shared native foundation. US1 follows the
foundation; US2 follows group interfaces; US3 consumes effective stage resolution. T017 can
run independently against the approved contract. T018 precedes completion; T019–T020 follow
integration. T021 has completed real-run evidence in verification-2026-09-28.md.

Within US1, example-generator work and config composition tests can be prepared independently
once group shape is fixed. Within US2, comparison adaptation can run separately from train/task
adaptation with shared resolver ownership assigned. Within US3, mocked publication tests can
be prepared independently of persistent-manifest implementation. Shared-file edits require a
single owner and integration review.

## Implementation strategy

Deliver configuration composition and generator behavior first, then stage integration, then
native artifact recording. Verify each story with focused lightweight tests before integration.
Preserve user's changes and dependency pins; never infer heavy-test authorization from elapsed time.

## Phase 7: Convergence

- [x] T022 Reject explicitly owned prediction model/project/name in src/clearml_yolo/tasks/compare.py per FR-006 (contradicts).
- [x] T023 Isolate retained comparison manifests by cache identity in src/clearml_yolo/comparison/reinfer.py per FR-009 (partial).
- [x] T024 Comment prediction-only rendering keys in training YAML in src/clearml_yolo/native_config.py per FR-005 (partial).

## Phase 8: Live verification findings

- [x] T025 Restore fresh-process config registration in src/clearml_yolo/apps/common.py and test every generated command in a subprocess per FR-003/SC-001 (contradicts).
