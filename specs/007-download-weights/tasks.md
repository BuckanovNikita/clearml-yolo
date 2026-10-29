# Tasks: Native weight preparation

## Setup and shared contracts

- [x] T001 Inspect current code, instructions, SDK discovery and portable skill in specs/007-download-weights/research.md.
- [x] T002 Record specification, architecture and dependent work in specs/007-download-weights/plan.md and architecture.json.
- [x] T003 Establish pure native request/result contracts in src/clearml_yolo/core/assets.py; validate architecture plan before implementation.

## User Story 1: Native preparation

- [x] T004 [US1] Add failing native destination/promotion tests in tests/test_native_assets.py.
- [x] T005 [US1] Implement narrow storage, resolver promotion and YOLO/RF native discovery in src/clearml_yolo/adapters/assets and backend assets modules.
- [x] T006 [P] [US1] Implement native timm/HF discovery, endpoint-scoped downloads/metadata and tests in adapters/assets/hub.py, adapters/torchvision/assets.py and tests/test_hub_assets.py.
- [x] T007 [US1] Integrate SDK/peer/classification contracts in .importlinter and tests/test_architecture.py.

## User Story 2: Command and automatic preparation

- [x] T008 [P] [US2] Add failing catalogue/state/CLI tests in tests/test_weight_preparation.py after T003.
- [x] T009 [US2] Implement catalogue filtering, deduplication, receipts, interruption and concurrency in adapters/assets/preparation.py.
- [x] T010 [US2] Add entrypoints/download_weights.py and pipeline-only execution invocation in entrypoints/hydra/common.py; register pyproject.toml script.

## User Story 3: Native configuration compatibility

- [x] T011 [US3] Verify custom Hydra values, boolean pretrained, explicit paths and resume preservation in tests/test_weight_preparation.py and tests/test_native_assets.py.
- [x] T012 [US3] Download real weights and verify fresh offline native loaders, YOLO aliases/custom YAML/inference/AMP, changed cwd, relative/absolute caches and worker execution; record native-verification.md and verification.md.
- [x] T013 [US3] Verify native Torchvision/timm/RF-DETR/DEIM reuse and real training path as required; record native-verification.md and verification.md.

## Documentation update and acceptance

- [x] T014 Update README.md and docs/model-assets.md, filesystem-policy.md, project-contracts.md and current-contracts.md as affected.
- [x] T015 Update authoritative portable clearml-yolo SKILL.md and usage/evaluation references; validate package/examples and record companion evidence.
- [x] T016 Run canonical application/docs gates and applicable mutation checks; reconcile all task-owned paths and architecture record in verification.md.
- [x] T017 Verify latest paired CY/cy-queue sources with proposed release versions using normal resolution, installed metadata and integration suite.
- [x] T018 Obtain fresh independent review after integration/verification; resolve findings, validate architecture acceptance and record review.md.
- [ ] T019 Complete authorized Conventional Commit and native Git-only release; verify remote branch/tag refs and preserve local overrides.

## Dependencies and parallel execution

T001–T003 precede all implementation. T004 precedes T005; T006 and T008–T010 may
run concurrently after shared contracts with exclusive files. T007 integrates their
imports. T011–T013 follow integration. T014/T015 may proceed alongside verification
using final interfaces. T016/T017 precede fresh T018; T019 follows all acceptance.
Each bounded agent must preserve others' files and may not delegate further.

## Requirement coverage

FR-001/002: T008–T010. FR-003/004: T004–T007,T012–T013.
FR-005/006: T008–T010. FR-007: T011–T013. FR-008: T006,T012.
FR-009: T004–T005,T007,T014. SC-001–004: T011–T019.
