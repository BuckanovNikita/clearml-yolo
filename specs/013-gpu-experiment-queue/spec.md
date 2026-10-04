# Feature Specification: GPU experiment queue

**Feature Branch**: `013-gpu-experiment-queue`

**Created**: 2026-10-02

**Status**: Approved for implementation

**Input**: Add a user-wide, same-operating-system NVIDIA GPU queue for model commands, with
strict FIFO admission, whole-device reservations, safe process ownership, native-device
normalization, concurrent Hydra jobs, and a pipeline transition from multi-GPU training to
single-GPU inference.

## User Scenarios & Testing

### User Story 1 - Submit GPU work without collisions (Priority: P1)

A user starts one or more GPU-backed pipeline, training, prediction, validation, or comparison
commands. Each request waits in submission order until its complete GPU demand can be reserved,
then runs in a fresh child process with concrete local device indices.

**Why this priority**: Collision-free admission is the core user value and safety boundary.

**Independent Test**: Submit requests with overlapping demand on a multi-GPU host and observe
strict head-of-line FIFO admission, atomic whole-device reservations, concurrent execution only
when requests fit, and release after the owning child exits.

**Acceptance Scenarios**:

1. **Given** two free GPUs and queued demands of two then one, **When** only one GPU is free,
   **Then** neither request bypasses the head; the two-GPU request starts atomically when both are
   free and the later request starts only when it reaches the head and fits.
2. **Given** multiple head requests that fit after earlier admissions, **When** their GPU sets do
   not overlap, **Then** several jobs run concurrently.
3. **Given** an NVIDIA device used by an external compute process, **When** admission is evaluated,
   **Then** that device is not reserved.
4. **Given** GPU telemetry cannot establish safe availability, **When** a request reaches
   admission, **Then** it remains unadmitted and reports a failure rather than assuming GPUs are
   free.

---

### User Story 2 - Preserve native device intent and provenance (Priority: P1)

A user keeps using native Ultralytics device values. GPU demand is derived from those values,
while requested settings remain visible and effective child settings record the concrete devices
actually assigned by the queue.

**Why this priority**: Existing command configuration must remain understandable and replayable.

**Independent Test**: Exercise every supported integer, list, string, null, empty, CPU, MPS, and
automatic device form and compare requested settings, derived demand, and child-local settings.

**Acceptance Scenarios**:

1. **Given** training device values `2`, `[0,1]`, `null`, an empty value, `cuda`, or automatic
   `-1` forms, **When** demand is derived, **Then** they request respectively one, two, one, one,
   one, or the count of automatic entries, without binding automatic entries to their written
   numeric value.
2. **Given** training device `cpu` or `mps`, **When** the command starts, **Then** it requests zero
   GPUs and begins immediately outside the queue.
3. **Given** GPU-backed prediction, validation, or comparison, **When** it starts, **Then** it
   requests exactly one GPU regardless of the written native GPU selector.
4. **Given** an admitted child, **When** configurations are recorded, **Then** requested device
   provenance remains separate from effective concrete child-local native indices.

---

### User Story 3 - Complete a pipeline without retaining idle training GPUs (Priority: P2)

A multi-GPU pipeline trains natively, waits for verified completion and distributed-worker
cleanup, retains the first assigned GPU for downstream inference, releases the others, and routes
all inference through child-local device `0`.

**Why this priority**: Long pipeline stages should return unused capacity without risking active
training workers or changing upstream behavior.

**Independent Test**: Run a two-or-more-GPU pipeline and prove that no device is released before
verified training/DDP cleanup, that all but the first are then reusable, and that the retained GPU
remains reserved until the pipeline child exits.

**Acceptance Scenarios**:

1. **Given** completed native training whose workers still appear in telemetry, **When** the
   pipeline requests transition, **Then** no reservation is released.
2. **Given** verified model completion and telemetry-confirmed worker cleanup, **When** transition
   occurs, **Then** GPUs two through N are released atomically, the first reservation is retained,
   and remaining prediction, validation, and comparison use child-local device `0`.
3. **Given** a single-GPU pipeline, **When** training completes, **Then** that GPU remains reserved
   through the remaining stages and job exit.

---

### User Story 4 - Run Hydra sweeps through the same queue (Priority: P2)

A user launches a BasicSweeper multirun for any model command. Jobs enter the shared FIFO in
submission order, each admitted job runs in a fresh child, and Hydra receives ordered results
without losing its per-job working directory, environment, or callbacks.

**Why this priority**: Sweeps are a common source of accidental oversubscription and must obey the
same safety contract as single runs.

**Independent Test**: Submit a mixed-demand BasicSweeper multirun and compare submission order,
admission order, fresh process identities, Hydra job directories, callback activity, and ordered
success/failure results.

**Acceptance Scenarios**:

1. **Given** a multirun with several jobs, **When** the launcher submits them, **Then** every job
   receives a monotonic queue ticket in Hydra submission order.
2. **Given** several jobs that can fit concurrently, **When** they are admitted, **Then** each runs
   in a fresh child while Hydra returns `JobReturn` records in original job order.
3. **Given** a child failure, **When** the sweep finishes, **Then** its ordered result is failed and
   the overall command returns nonzero while other admitted jobs clean up their reservations.

### Edge Cases

- A request larger than the visible supported GPU set is rejected before enqueue; there is no
  bypass, priority, timeout, or daemon policy.
- Stale queue and reservation entries are reclaimed only when the supervisor and child native
  liveness locks are both acquirable; age or PID alone is insufficient.
- An inherited `CUDA_VISIBLE_DEVICES` may contain indices or UUIDs; only that visibility mapping is
  isolated in a metadata subprocess before any job acquires a native GPU context.
- MIG devices and coordination across operating-system instances or hosts are unsupported.
- An unrelated process can start using a GPU after the final availability check, and a single
  admitted job can still exhaust memory.
- CPU-only commands, metrics, reports, ground-truth preparation, and configuration generation do
  not enter the queue.
- A crash, interruption, or supervisor loss must not leave a live child unowned or a dead child
  holding a permanent reservation.

## Requirements

### Functional Requirements

- **FR-001**: `cy`, `cy-train`, `cy-predict`, `cy-val`, and `cy-compare` MUST use one user-wide,
  same-operating-system queue for GPU-backed execution; other commands MUST start immediately.
- **FR-002**: Pending requests MUST use monotonically increasing tickets and strict FIFO
  head-of-line admission. Several requests MAY run concurrently only when each reaches the head
  and its entire non-overlapping demand fits.
- **FR-003**: Admission MUST reserve the full requested number of whole NVIDIA GPUs atomically.
  A demand larger than the supported visible set MUST fail before enqueue. Partial admission,
  priority, bypass, TTL expiry, and PID-only reclaim MUST NOT occur.
- **FR-004**: Availability MUST exclude GPUs with external compute users. Unknown or failed
  telemetry MUST fail closed.
- **FR-005**: Queue state MUST be user-wide and independent of `CY_HOME`, defaulting under the
  operating system's state location (`XDG_STATE_HOME` or `~/.local/state` on Unix-like systems;
  `LOCALAPPDATA` on Windows). An injectable internal root MAY isolate tests without creating a
  public command option.
- **FR-006**: Registry mutation MUST hold a native file lock only for short read-modify-write
  operations. Each supervisor and child MUST hold a native liveness lock for its lifetime; reclaim
  requires both locks to be acquirable and MUST NOT depend on TTL or PID-only decisions.
- **FR-007**: GPU discovery MUST honor inherited `CUDA_VISIBLE_DEVICES` and map the visible set to
  stable GPU UUIDs using an isolated metadata subprocess before the execution child imports or
  initializes native model runtimes.
- **FR-008**: Training demand MUST derive from native device values as follows: integer `2` means
  one GPU; list `[0,1]` means two; each automatic `-1` entry contributes one without binding that
  written ID; null, empty, or `cuda` means one; `cpu` and `mps` mean zero. GPU-backed inference
  commands MUST demand exactly one GPU.
- **FR-008a**: A pipeline's initial demand MUST be the maximum of its training demand and one when
  any enabled downstream inference stage is GPU-backed. CPU training followed by GPU inference
  MUST therefore reserve one GPU before the job starts and MUST NOT reacquire mid-pipeline.
- **FR-009**: An admitted job MUST run in a fresh child process with assigned physical devices
  exposed as its visible set and concrete child-local native indices. Requested and effective
  device settings MUST be retained separately for provenance.
- **FR-010**: Waiting MUST occur before ClearML task creation and before native GPU context. Each
  admitted execution child MUST own exactly one ClearML task and its existing native lifecycle.
- **FR-011**: After verified native training completion and telemetry-confirmed DDP cleanup, a
  pipeline MUST retain its first assigned GPU, atomically release N-1 remaining GPUs, route all
  later inference to child-local device `0`, and retain the first reservation through child exit.
- **FR-011a**: GPU prediction and comparison MUST both use retained child-local device `0`. When
  downstream inference is CPU-only, a GPU training pipeline MUST retain the first assignment
  until child exit.
- **FR-012**: The pipeline transition MUST use supported application boundaries and MUST NOT
  monkeypatch Ultralytics or change the approved upstream dependency revision.
- **FR-013**: The five model commands MUST default to a queue-aware Hydra local launcher that
  supports BasicSweeper only, submits jobs FIFO, admits independent fresh children concurrently
  when capacity permits, preserves per-job callbacks/environment/directory and chdir semantics,
  and returns ordered `JobReturn` statuses.
- **FR-014**: A failed child or sweep job MUST propagate a nonzero result and release task-owned
  reservations. Supervisor interruption MUST preserve deterministic ownership and cleanup.
- **FR-015**: The feature MUST NOT add a daemon, bypass, priority, separate GPU-count setting,
  MIG support, or cross-host/cross-operating-system coordination.
- **FR-016**: Documentation and validation MUST distinguish intended behavior from exercised
  evidence; multi-GPU, ClearML, DDP, and upload claims require dated native evidence.

### Key Entities

- **Queue request**: Monotonic ticket, requested GPU count, supervisor identity, child identity,
  lifecycle state, and submission metadata.
- **GPU reservation**: Atomic ownership of one or more stable GPU UUIDs by one live request.
- **GPU inventory snapshot**: Visible UUID ordering and external compute-use telemetry from NVML;
  inherited visibility mapping alone is isolated in a metadata subprocess.
- **Execution child**: Fresh process that receives concrete local device indices, creates one
  ClearML task, and owns native execution and exit status.
- **Pipeline reservation phase**: Training allocation followed by the optional retain-one
  inference allocation after verified cleanup.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In deterministic contention scenarios, 100% of admissions follow ticket order; no
  later request starts while the head request is waiting for its full demand.
- **SC-002**: Across interruption, crash, and stale-state scenarios, no held native liveness lock
  loses a reservation and every ownership pair whose two locks are acquirable is reclaimable
  without elapsed-time assumptions.
- **SC-003**: Every supported device form produces the demand defined in FR-008, and every
  admitted child records requested provenance plus concrete effective settings.
- **SC-004**: A multi-GPU pipeline releases exactly N-1 GPUs only after verified training/DDP
  cleanup and retains exactly one GPU through all remaining stages and process exit.
- **SC-005**: BasicSweeper results preserve submission order and report every job's success or
  failure while all reservations are released after job completion.
- **SC-006**: Focused tests, repository gates, documentation/link checks, and required dated
  native evidence pass before implementation is reported as exercised.

## Assumptions

- All participating queue clients share one user account and one operating-system filesystem.
- NVML can identify whole NVIDIA GPUs and active compute users on supported systems.
- Existing native command configuration remains the source of GPU demand; users do not configure
  a second scheduler-specific count.
- Strict head-of-line behavior is intentional even when a later smaller job could run sooner.
- The queue reduces cooperative collisions but cannot prevent races with uncoordinated processes
  after admission or guarantee that an admitted workload fits GPU memory.
