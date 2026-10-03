# Tasks: GPU experiment queue

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts](contracts/)

**Tests**: Required because scheduling, process liveness, GPU ownership, and lifecycle transitions
are safety-critical and explicitly require deterministic and native acceptance evidence.

## Phase 1: Setup and governance

**Purpose**: Establish dependency, packaging, contract, and governance prerequisites.

- [x] T001 Amend the scheduling prohibition narrowly and preserve amendment history as constitution 7.0.0 in `.specify/memory/constitution.md` (FR-001–FR-016).
- [x] T002 Declare direct `nvidia-ml-py` runtime dependency and package modules `clearml_yolo` plus `hydra_plugins.cy_queue` in `pyproject.toml` and `uv.lock` without changing the approved `digital-metrics` source/revision (FR-004, FR-007, FR-013).

---

## Phase 2: Foundational resource and queue contracts

**Purpose**: Implement deterministic demand, inventory, durable ownership, and atomic admission.

**CRITICAL**: No queued app or launcher work can complete before this phase.

- [x] T003 [P] Write failing normalization, inherited visibility, UUID mapping, external-compute-user, MIG-rejection, and telemetry-failure tests in `tests/test_gpu_resources.py` (FR-004, FR-007, FR-008, FR-008a).
- [x] T004 [P] Write failing registry validation, oversized-demand rejection, monotonic-ticket, strict-head FIFO, concurrent-fit, atomic-N, supervisor/child native-liveness-lock, contraction, and release tests plus a subprocess helper in `tests/test_gpu_queue.py` and `tests/gpu_queue_worker.py` (FR-002, FR-003, FR-005, FR-006, FR-011, FR-011a, FR-014).
- [x] T005 Implement typed native-device demand normalization, direct NVML telemetry, and isolated inherited-visibility mapping in `src/clearml_yolo/gpu_resources.py`; preserve constraints "integer `2` means one GPU", "list `[0,1]` means two", "each automatic `-1` contributes one without binding its ID", "null/empty/`cuda` means one", and "`cpu`/`mps` means zero" (FR-004, FR-007, FR-008, FR-008a; depends on T003).
- [x] T006 Implement the validated user-wide registry, OS state-root resolution, internal injectable test root, short native-lock transactions, monotonic tickets, pre-enqueue oversized-demand rejection, strict-head multi-admission, atomic reservations, supervisor/child native liveness locks, fail-closed recovery, contraction, and release in `src/clearml_yolo/gpu_queue.py` (FR-002, FR-003, FR-005, FR-006, FR-011, FR-011a, FR-014; depends on T004, T005).

**Checkpoint**: Resource discovery and queue state pass deterministic tests without importing native model runtimes.

---

## Phase 3: User Story 1 - Submit GPU work without collisions (Priority: P1)

**Goal**: Queue the five GPU-backed model commands and run each admitted job in a fresh child.

**Independent Test**: Competing requests admit strictly FIFO with non-overlapping UUID sets, while
CPU-only and non-model commands bypass the registry and child failures release reservations.

- [x] T007 [P] [US1] Write failing supervisor/child boundary tests for pre-ClearML waiting, pre-native-context probing, visibility assignment, spawn failure, interruption, nonzero propagation, and terminal cleanup in `tests/test_gpu_execution.py` and `tests/test_gpu_supervision.py` (FR-001, FR-009, FR-010, FR-014).
- [x] T008 [US1] Implement fresh-child queued supervision and worker execution, requested/effective device separation, ClearML/native ownership boundary, process-tree cancellation, and unconditional supervisor cleanup in `src/clearml_yolo/apps/execution.py` and `src/clearml_yolo/apps/job_worker.py` (FR-001, FR-009, FR-010, FR-014; depends on T005–T007).
- [x] T009 [US1] Route shared preparation and `cy`, `cy-train`, `cy-predict`, `cy-val`, and `cy-compare` through the queued execution seam while keeping other commands immediate in `src/clearml_yolo/apps/common.py`, `src/clearml_yolo/apps/pipeline.py`, `src/clearml_yolo/apps/train.py`, `src/clearml_yolo/apps/predict.py`, `src/clearml_yolo/apps/val.py`, and `src/clearml_yolo/apps/compare.py` (FR-001, FR-008, FR-010; depends on T008).

**Checkpoint**: Single-run model commands obey queue admission and preserve one child-owned task.

---

## Phase 4: User Story 2 - Preserve device intent and provenance (Priority: P1)

**Goal**: Derive demand from native configuration and record concrete child-local assignments without losing requested values.

**Independent Test**: Every supported selector produces the required count and the admitted child records separate requested and effective native settings.

- [x] T010 [P] [US2] Extend requested/effective configuration tests for concrete child-local training indices plus inference local `0` in `tests/test_gpu_execution.py` and `tests/test_config_upload_commands.py` (FR-008, FR-008a, FR-009).
- [x] T011 [US2] Integrate demand derivation and effective child device overrides with application configuration recording in `src/clearml_yolo/apps/execution.py` without mutating requested configuration (FR-008, FR-008a, FR-009; depends on T008, T010).

**Checkpoint**: Device demand, requested provenance, and effective native execution settings are independently inspectable.

---

## Phase 5: User Story 3 - Contract pipeline reservations safely (Priority: P2)

**Goal**: Release unused training GPUs after verified native/DDP cleanup and retain stable downstream capacity.

**Independent Test**: A multi-GPU pipeline retains all devices while any worker is active, then
atomically releases N-1 and routes GPU prediction/comparison through retained local `0` until exit.

- [x] T012 [P] [US3] Write failing pipeline-demand, verification-order, DDP-telemetry, N-to-one contraction, CPU-train/GPU-inference, GPU-train/CPU-inference, and retained-device routing tests in `tests/test_pipeline.py`, `tests/test_gpu_execution.py`, `tests/test_gpu_queue.py`, and `tests/test_gpu_resources.py` (FR-008a, FR-011, FR-011a, FR-012).
- [x] T013 [US3] Add invocation-scoped reservation ownership and the supported reservation-transition callback in `src/clearml_yolo/gpu_runtime.py`, then integrate pipeline demand/routing in `src/clearml_yolo/tasks/pipeline.py` and `src/clearml_yolo/apps/execution.py` without monkeypatching Ultralytics (FR-008a, FR-011, FR-011a, FR-012; depends on T006, T011, T012).

**Checkpoint**: Pipeline capacity contraction is gated by model verification and telemetry-confirmed worker cleanup.

---

## Phase 6: User Story 4 - Queue BasicSweeper jobs (Priority: P2)

**Goal**: Make the queue-aware local Hydra launcher the default for all model commands.

**Independent Test**: A multirun starts fresh children as FIFO capacity permits, preserves Hydra
job context, returns ordered results, and exits nonzero when any job fails.

- [x] T014 [P] [US4] Write failing plugin discovery, five-command default, FIFO submission, concurrent child, callback, environment, output-directory, chdir, ordered-`JobReturn`, and failure-status tests in `tests/test_hydra_queue_launcher.py` and `tests/test_configs.py` (FR-013, FR-014).
- [x] T015 [US4] Implement the BasicSweeper-compatible queue launcher in `src/hydra_plugins/cy_queue/__init__.py` and `src/hydra_plugins/cy_queue/launcher.py` (FR-013, FR-014; depends on T008, T014).
- [x] T016 [US4] Register the queue-aware launcher defaults for exactly the five model applications in `src/clearml_yolo/configs.py` (FR-001, FR-013; depends on T015).

**Checkpoint**: Single runs and BasicSweeper multiruns share admission, isolation, cleanup, and result semantics.

---

## Phase 7: Verification and native evidence

**Purpose**: Prove deterministic behavior, packaging, repository quality, and real multi-GPU lifecycle behavior.

- [x] T017 Run focused queue/resource/execution/launcher/pipeline tests, then full `pytest`, Ruff, strict mypy, and import-linter; resolve only feature-caused failures in the affected source/tests (FR-001–FR-015; depends on T009, T011, T013, T016).
- [x] T018 Build the wheel and verify that both `clearml_yolo` and `hydra_plugins.cy_queue` install and import from the artifact in `pyproject.toml` packaging output (FR-013; depends on T002, T016, T017).
- [x] T019 Run the isolated same-user multi-GPU/ClearML/DDP scenarios from `specs/013-gpu-experiment-queue/quickstart.md`, clean task-owned resources, and record actual results and unavailable gates in a dated `specs/013-gpu-experiment-queue/verification-YYYY-MM-DD.md` (FR-004, FR-007, FR-010–FR-016; depends on T017, T018).

---

## Phase 8: Documentation update and acceptance

**Purpose**: Reconcile maintained contracts with verified implementation and complete project documentation gates.

- [x] T020 Update current queue, command, requested/effective device, lifecycle, and filesystem guidance in `README.md`, `docs/project-contracts.md`, `docs/current-contracts.md`, `docs/filesystem-policy.md`, `specs/005-explicit-detection-config/contracts/native-configuration.md`, and `specs/007-detection-config-cleanup/contracts/configuration-and-artifacts.md` based on the final implementation (FR-001–FR-016; depends on T009, T011, T013, T016).
- [x] T021 Update portable native acceptance prerequisites in `.agents/skills/running-end-to-end-tests/references/pipeline-prerequisites.md`, preserving machine-specific values outside the repository (FR-016; depends on T019, T020).
- [x] T022 Validate all changed Markdown, local links, and documented command/configuration examples; record the exact documentation checks in `specs/013-gpu-experiment-queue/verification-YYYY-MM-DD.md` (FR-016; depends on T019–T021).
- [x] T023 Re-run Spec Kit consistency analysis, inspect the combined diff, and obtain a fresh independent read-only review before acceptance in `specs/013-gpu-experiment-queue/analysis.md` (FR-001–FR-016; depends on T017–T022).

## Dependencies and execution order

- T001 and T002 are governance/packaging prerequisites and may proceed in parallel.
- T003 and T004 are independent failing-test tasks. T005 precedes T006 because queue admission
  consumes normalized inventory and demand.
- US1 establishes the execution seam. US2, US3, and US4 depend on that seam; US2 configuration work
  and US4 launcher work can proceed in parallel. US3 depends on US2 effective routing.
- Verification follows all implementation stories. Native evidence follows deterministic gates and
  package verification. Documentation follows the actual implementation and native evidence.
- Final acceptance follows implementation, verification, native evidence, and documentation
  validation; implementation checkboxes remain pending until the parent records evidence.

## Parallel examples

- Resource phase: T003 and T004 can run concurrently in separate test files.
- After T008: T010/T011 device provenance work and T014/T015 launcher work have separate primary
  ownership; T012 can prepare pipeline tests while T011 completes.
- Documentation drafting for T020 can begin after implementations stabilize, but T021/T022 cannot
  complete until dated native outcomes are known.

## Implementation strategy

The MVP is US1 plus foundational demand and queue state: collision-free FIFO admission for one
model invocation. Add provenance, pipeline contraction, and BasicSweeper integration incrementally.
Do not report the feature complete until all four stories, deterministic gates, packaging,
mandatory documentation, and required dated native evidence are complete.

## Implementation evidence

T001–T021 are recorded in [dated verification](verification-2026-10-02.md). T019 records available
native runs and unavailable gates; physical multi-GPU/DDP and Windows outcomes are not claimed.
T022 documentation validation passed; T023 independent read-only review returned `ship`, with no
blocking findings. All written-requirement checklist items were approved. Native hardware limits
remain explicit in the dated evidence.
