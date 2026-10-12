# Tasks: Multi-model detection backends

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [backend contract](contracts/backend.md) and
[export contract](contracts/export.md).

**Status**: Implementation ledger. An unchecked item is not complete; planning artifacts
and mocked tests alone do not establish native acceptance.

**Format**: `[ID] [P?] [Story?] Description with owned paths`. `[P]` means independent
work can proceed after the explicitly stated prerequisite, not permission to race on
shared files. Tests below are required by the approved acceptance specification.

## Phase 1: Setup and early feasibility

- [x] T001 Record inherited v0.23.0/follow-up state and protected dependency overrides in `specs/025-multi-model-backends/research.md`; preserve existing work.
- [x] T002 [P] Prove RF-DETR 1.11.2 and approved DEIMv2 revision import, short native fit, reload and prediction on the chosen stack; record portable evidence in `specs/025-multi-model-backends/verification.md` and machine details outside the repository.
- [x] T003 [P] Prove actual dynamic ResNet-50 and DINO Faster R-CNN ONNX/build/inference with rectangular inputs and batch four; record operator/parity findings in `specs/025-multi-model-backends/verification.md` without concurrent file writes with T002.
- [x] T004 Resolve feasibility findings before preset expansion and declare verified optional dependencies in `pyproject.toml` and `uv.lock`, preserving approved external revisions and local source overrides.

## Phase 2: Shared foundation

**Gate**: T002/T003 critical feasibility failures block broad implementation; no silent
scope reduction. Parent owns all shared edits in this phase.

- [x] T005 Add project-owned selection, descriptor, profile and execution records in `src/clearml_yolo/application/contracts.py` and `src/clearml_yolo/core/execution.py`; enforce "Unknown backend/preset combinations and unsupported settings fail explicitly."
- [x] T006 Generalize model/dataset/repository ports in `src/clearml_yolo/application/ports.py` and lazy composition in `src/clearml_yolo/entrypoints/composition.py` without SDK imports in application/core/configuration.
- [x] T007 Extend architecture classification and lazy-import regression cases in `pyproject.toml` and `tests/test_architecture.py` for the new adapter/export packages.
- [x] T008 Add deterministic COCO and detection-record preparation in `src/clearml_yolo/adapters/storage/dataset_export.py` and `src/clearml_yolo/adapters/storage/dataset_records.py`; enforce "Public labels remain exact strings; background is not a public class."
- [x] T009 Extend format/vocabulary cache identity and tests in `src/clearml_yolo/adapters/storage/dataset_cache.py` and `tests/test_dataset_cache.py`, covering empty images, splits, coordinates and unchanged source bytes.
- [x] T010 Add descriptor persistence and download binding in `src/clearml_yolo/adapters/storage/` and `src/clearml_yolo/adapters/clearml/models.py`; enforce "Descriptor/checkpoint hash or backend/preset disagreement fails before execution."
- [x] T011 Register lazy model preset groups in `src/clearml_yolo/entrypoints/hydra/configs.py` and test typed train/predict selection in `tests/test_configs.py`, leaving default YOLO groups authoritative.

## Phase 3: User Story 1 — Native training and evaluation (Priority: P1)

**Goal**: All advertised native families complete the existing workflow.

**Independent test**: Actual short training, fresh best-checkpoint download/reload,
prediction and validation for every listed preset, with one owner task/model.

- [x] T012 [P] [US1] Add DEIMv2 source/revision, class mapping, effective recipe and failure tests in `tests/test_deim_backend.py` after T005–T011.
- [x] T013 [P] [US1] Add RF-DETR callback, best-checkpoint, class mapping and failure tests in `tests/test_rfdetr_backend.py` after T005–T011.
- [x] T014 [P] [US1] Add Faster R-CNN feature-shape, loss/update, vocabulary and reload tests in `tests/test_fasterrcnn_backend.py` after T005–T011.
- [x] T015 [P] [US1] Implement private verified DEIMv2 loading and S/M/L/X native training/inference in `src/clearml_yolo/adapters/deim/`, including any necessary project-owned transform bridge without upstream patches.
- [x] T016 [P] [US1] Implement Nano/Small/Medium/Large native RF-DETR training/inference and owner telemetry in `src/clearml_yolo/adapters/rfdetr/` using the approved API.
- [x] T017 [P] [US1] Implement Faster R-CNN ResNet-50/101-FPN, ConvNeXt-Tiny, Swin-Tiny and DINOv2/DINOv3-Small backbones, explicit pyramids and task heads in `src/clearml_yolo/adapters/fasterrcnn/`.
- [x] T018 [US1] Integrate dataset selection, effective native settings and result propagation in `src/clearml_yolo/application/use_cases/train.py`, `predict.py`, `val.py` and `pipeline.py` while retaining existing YOLO behavior.
- [x] T019 [US1] Integrate one owner task, callback relay, selected best Output Model and verified upload/flush in `src/clearml_yolo/adapters/clearml/` and `src/clearml_yolo/adapters/integrations/`; retain diagnostics on failures.
- [x] T020 [US1] Execute DEIMv2 S/M/L/X native short training/reload/predict/validate and fresh ClearML download matrix; record each outcome in `specs/025-multi-model-backends/verification.md`.
- [x] T021 [US1] Execute RF-DETR Nano/Small/Medium/Large native short training/reload/predict/validate and fresh ClearML download matrix; record each outcome in `specs/025-multi-model-backends/verification.md`.
- [x] T022 [US1] Execute Faster R-CNN ResNet-50-FPN, ResNet-101-FPN, ConvNeXt-Tiny, Swin-Tiny, DINOv2-Small and DINOv3-Small native short training/reload/predict/validate and fresh ClearML download matrix; record each outcome in `specs/025-multi-model-backends/verification.md`.
- [x] T023 [US1] Verify original YOLO native commands, dataset cache reuse and callback/upload/flush/interruption failures in `tests/test_native_runtime.py`, relevant ClearML tests and `specs/025-multi-model-backends/verification.md`.

## Phase 4: User Story 2 — Cross-family comparison (Priority: P1)

**Goal**: Independently resolve candidate/baseline families while preserving scientific policy.

**Independent test**: Each new backend versus YOLO and another new family on the same
current images, with exact frozen thresholds and shared inference device.

- [x] T024 [US2] Extend `ModelRef`/resolved metadata and comparison contract tests in `src/clearml_yolo/application/contracts.py` and `tests/test_compare.py`, covering raw external overrides, legacy YOLO and descriptor conflicts.
- [x] T025 [US2] Resolve both comparison backends independently in `src/clearml_yolo/application/use_cases/compare.py` and composition, binding one shared inference device and requested policy.
- [x] T026 [US2] Extend backend/preprocessing cache identity and effective evidence in `src/clearml_yolo/application/use_cases/compare.py`; reject unsupported requested settings and retain same-current-image membership.
- [x] T027 [US2] Verify unchanged validation-only calibration, exact baseline thresholds, canonical CSVs and paired reports in comparison/evaluation tests under `tests/`.
- [x] T028 [US2] Execute DEIMv2↔YOLO, RF-DETR↔YOLO, Faster R-CNN↔YOLO and DEIMv2↔RF-DETR, RF-DETR↔Faster R-CNN, Faster R-CNN↔DEIMv2 comparisons; record evidence in `specs/025-multi-model-backends/verification.md`.

## Phase 5: User Story 3 — Scheduling, isolation and configuration (Priority: P1)

**Goal**: All backend operations obey released admission, replay and ownership contracts.

**Independent test**: Four execution modes per backend plus CPU, cancellation, replay,
mixed-family sweeps and safe selected configuration export.

- [x] T029 [US3] Extend lightweight phase/device-path demand extraction and tests in `src/clearml_yolo/adapters/runtime/gpu_scheduling.py`, `src/clearml_yolo/core/execution.py` and `tests/test_gpu_scheduling.py`.
- [x] T030 [US3] Extend child-local remapping, exact identities, requested/effective provenance and replay guards in `src/clearml_yolo/entrypoints/hydra/execution.py` and worker/launcher integration; enforce "No SDK import, CUDA initialization or task creation occurs before admission."
- [x] T031 [US3] Select backend-specific runtime initialization inside generic invocation isolation in `src/clearml_yolo/entrypoints/hydra/common.py` and `src/clearml_yolo/adapters/integrations/native_runtime.py`.
- [x] T032 [US3] Verify owned descendant reaping before memory cleanup/reservation contraction and bounded FiftyOne lifecycle in `tests/test_gpu_supervision.py`, `tests/test_native_runtime.py` and `tests/test_runtime_bootstrap.py`.
- [x] T033 [US3] Add `--model` and `cy-export` selected configuration generation in `src/clearml_yolo/entrypoints/config_tree.py` and `src/clearml_yolo/entrypoints/hydra/config_tree.py`; retain default YOLO inventory, preflight and symlink protections.
- [x] T034 [US3] Verify SDK-free helps/config export and all selected inventories/overwrite paths in `tests/test_config_tree.py` and `tests/test_runtime_entrypoints.py`.
- [x] T035 [US3] Execute all four queue/autogpu modes for each new backend, CPU telemetry bypass, exact remapping, replay restrictions, cancellation and training cleanup; record outcomes in `specs/025-multi-model-backends/verification.md`.
- [x] T036 [US3] Execute mixed-family queued and direct Hydra sweeps, isolation-conflict/failure cases and bounded publication checks; record ordered results/output/callback evidence in `specs/025-multi-model-backends/verification.md`.

## Phase 6: User Story 4 — Standalone Faster R-CNN export (Priority: P1)

**Goal**: All six Faster R-CNN presets build and run dynamic standalone FP32/FP16 engines.

**Independent test**: Every required profile size/batch and quality gate passes in a
Torch-free runtime; local and target compatibility claims remain distinct.

- [x] T037 [US4] Add typed export request/result validation and GPU phase semantics in `src/clearml_yolo/application/contracts.py` and `tests/test_export.py`, including required operation inputs and CPU rejection for build/verify.
- [x] T038 [P] [US4] Implement shared native/export normalization, canvas/valid-size and original-box restoration in `src/clearml_yolo/adapters/fasterrcnn/`; enforce "Batch is an integer from 1 through 4; shapes must fit one complete profile."
- [x] T039 [P] [US4] Implement dynamic tensor ONNX export with proposals, ROI and NMS inside the graph in `src/clearml_yolo/adapters/export/`, preserving DINO interpolation/rotary semantics and recording operator/plugin requirements.
- [x] T040 [US4] Implement TensorRT 10.13.0 FP32/FP16 builds, both min/opt/max profiles and metadata/hash validation in `src/clearml_yolo/adapters/export/` after T038/T039.
- [x] T041 [US4] Produce a Torch-free and ClearML-free standalone runner with explicit counts, shape validation and profile switching in `src/clearml_yolo/adapters/export/`; no native fallback.
- [x] T042 [US4] Implement `cy-export` ONNX/build/verify orchestration in `src/clearml_yolo/application/use_cases/export.py`, `src/clearml_yolo/entrypoints/export.py`, Hydra registration and `pyproject.toml` with one task and no trained-model duplication.
- [x] T043 [US4] Implement checkpoint/corpus/preprocessing/evaluator-bound verification reporting in `src/clearml_yolo/adapters/export/`; enforce "An all-empty or all-zero native reference does not satisfy the quality gate."
- [x] T044 [US4] Verify finite outputs, available raw differences, class-aware one-to-one matching, coordinate restoration and quality-loss distinction in `tests/test_export.py` using meaningful input/output fixtures.
- [x] T045 [US4] Execute all six Faster R-CNN FP32/FP16 engines at 960×608, 960×736, 1536×128 and 1920×256, batches 1–4, interior shapes, repeated switches, empty/crowded cases and rejection cases; record each in `specs/025-multi-model-backends/verification.md`.
- [x] T046 [US4] Run serialized engines in a fresh Torch-free environment and prove no detector fallback; record standalone evidence in `specs/025-multi-model-backends/verification.md`.
- [x] T047 [US4] Measure quality on identical meaningful labeled data, require mAP50–95 loss ≤0.001 FP32/≤0.005 FP16 and report per-class recall/latency/memory; distinguish local execution from untested CUDA 11.8 deployment in `specs/025-multi-model-backends/verification.md`.
- [x] T048 [US4] Force-download export artifacts/reports and validate source lineage, one task, zero extra trained models and failure cleanup in `specs/025-multi-model-backends/verification.md`.

## Phase 7: Parent integration and independent review

- [x] T049 Inspect the combined task-owned diff and run complete pytest, Ruff, strict mypy, import-linter, build/install and command/configuration checks; record exact evidence in `specs/025-multi-model-backends/verification.md`.
- [x] T050 Obtain fresh independent read-only review after T049, covering implementation/spec consistency, all unverified gates and preserved changes; record findings and resolutions in `specs/025-multi-model-backends/review.md`.
- [x] T051 Resolve review findings in their owning source/tests, rerun affected checks and reconcile remaining work in `specs/025-multi-model-backends/tasks.md` without erasing completed history.

## Phase 8: Mandatory documentation update and release

**Gate**: This final phase depends on implemented behavior and verified evidence. No
completion claim or release while required documentation/examples or native gates fail.

- [x] T052 Update `docs/project-contracts.md`, `docs/current-contracts.md`, `docs/runtime-isolation.md`, affected configuration/GPU/publication/recovery contracts and active specifications to match verified behavior; preserve dated history.
- [x] T053 [P] Write model/configuration/backbone guidance in `docs/multi-model-backends.md` and update Russian user documentation in `README.md` after implementation stabilizes.
- [x] T054 [P] Write `docs/tensorrt-deployment.md` with exact verified dependency/plugin versions, CUDA 11.8 target rebuilding, dynamic profiles, standalone usage, operator limitations and explicit local-versus-target evidence.
- [x] T055 Update `.agents/skills/running-end-to-end-tests/SKILL.md` and its project-owned references, regenerate documented selected configuration examples and reconcile `specs/025-multi-model-backends/quickstart.md` with actual command behavior.
- [x] T056 Validate changed Markdown/local links and all changed command/configuration examples; record documentation scope/outcomes in `specs/025-multi-model-backends/verification.md`.
- [ ] T057 Run applicable pre-commit/release gates and inspect explicit task-scoped staged paths under `docs/development.md` commit procedure, preserving/restoring the exact local `[tool.uv.sources]` section unstaged; record final verification before commit.
- [ ] T058 Complete the authorized Conventional Commit/local release workflow using `scripts/local_release.py`, then explicitly push only the required branch and Git version tag after checks; do not create GitHub Release objects or upload assets/packages.

## Dependencies and execution order

- T002 and T003 are independent scratch investigations while the parent establishes T001;
  investigators send evidence to the single ledger owner. T004 integrates both gates.
- T005–T011 establish shared interfaces. Adapter owners may prepare bounded investigations
  earlier but implement against frozen interfaces. T015/T016/T017 are independent with
  separate adapter/test ownership. Parent handles T018/T019 and shared configuration/runtime.
- US2 implementation depends on shared resolution/contracts; native comparison acceptance
  depends on US1 working checkpoints. US3 develops alongside adapters after phase contracts
  stabilize. US4 graph work depends on Faster R-CNN features and the early export gate.
- All real GPU acceptance is sequential on shared hardware; do not overlap capacity-heavy
  probes/training/builds. One parent writes shared verification evidence to avoid collisions.
- T049 follows all story implementation and acceptance; T050 is a fresh reviewer after
  parent verification. T052–T056 are the mandatory final documentation stage; T057/T058
  follow all checks and release authorization, not a request for renewed permission.

## Parallel ownership examples

| Workstream | Exclusive writes | Dependencies and evidence |
| --- | --- | --- |
| Parent/shared | Core/application/composition, Hydra/runtime, storage/ClearML, dependency lock and shared evidence | Integrates all contracts, validates entire diff and performs final checks |
| DEIMv2 agent | `src/clearml_yolo/adapters/deim/`, `tests/test_deim_backend.py` | Frozen shared interfaces; native source/recipe/telemetry tests |
| RF-DETR agent | `src/clearml_yolo/adapters/rfdetr/`, `tests/test_rfdetr_backend.py` | Frozen shared interfaces; native trainer/reload/telemetry tests |
| Faster R-CNN/export agent | `src/clearml_yolo/adapters/fasterrcnn/`, `src/clearml_yolo/adapters/export/`, adapter/export tests | Feasibility gate and frozen records; dynamic engine/parity evidence |
| Independent reviewer | No writes | Fresh review after parent integration and verification |

Bounded agents do not delegate. Respect four active slots; sequence documentation/review
when adapter work ends. Shared-path changes require parent integration, not concurrent edits.

## Implementation strategy

Prove feasibility, freeze the minimum shared interface, integrate native families in
parallel and verify one complete native path before expanding the acceptance matrix.
US1 is the first useful increment; it is not the completion boundary because all four
approved stories and every preset/export gate are required. Keep failures explicit,
resolve them within scope, preserve unrelated work and never mark partial scaffolding as
feature completion. No deployment is authorized.

## Continuation status — 2026-10-11

The shared integration and focused-check tasks marked above are implemented with the
lightweight evidence in [verification.md](verification.md). Native adapter/export code
is present, but the per-preset execution and final acceptance tasks remain open. The early
independent [review](review.md) does not satisfy T050. No heavy workload may start before
2026-10-11 22:00 UTC (2026-10-12 01:00 Moscow); the parent must release prepared drivers
only after checking the clock. Final documentation validation and release remain pending.

The user subsequently lifted that hold with "can start now". The parent checked
2026-10-11 20:43:09 UTC and released workload preparation; GPU acceptance remains
sequential and subject to the existing shared admission contract.
