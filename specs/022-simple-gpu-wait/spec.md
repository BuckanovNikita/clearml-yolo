# Feature Specification: Simple GPU waiting

**Created**: 2026-10-10

**Status**: Accepted for implementation

**Input**: “Let's go first drop queue functional stay only awaiting of free gpu”

## User Scenarios & Testing

### User Story 1 - Run without a queue (Priority: P1)

Users start a command and wait only for enough free visible GPUs. The command
then executes directly, without a queue supervisor or a queued execution child.

**Independent test**: Simulate busy GPUs becoming free, verify execution starts
after availability, and verify the executing process is the invoking process.

**Acceptance scenarios**:

1. Busy GPUs delay model execution and ClearML task creation until sufficient
   devices are free; interruption while waiting exits without a task.
2. CPU/MPS and non-model commands start without GPU inventory access.
3. Successful execution returns normally; failures retain their original exception.

### User Story 2 - Keep native configuration and sweeps (Priority: P2)

Users retain native device-count settings and requested/effective provenance.
Local multiruns execute sequentially using Hydra's standard launcher.

**Independent test**: Compose each command, run a two-job local sweep, and check
execution order, outputs, device mapping and failure propagation.

### Edge Cases

- Impossible demand, unavailable telemetry, unsupported MIG or lost visibility fail clearly.
- Repeated jobs in one process must not wait for their own retained CUDA context.
- Concurrent commands can observe the same free GPU; availability is not a reservation.
- Replay cannot increase GPU demand beyond the devices checked before task creation.

## Requirements

- **FR-001**: Remove FIFO tickets, queue registries, reservations, contraction and
  queued job supervision from execution and distributions.
- **FR-002**: Poll supported whole-GPU availability before native runtime and task
  initialization, retaining existing count derivation and inherited CUDA visibility.
- **FR-003**: Run workflows in the calling process; CPU/MPS must not wait for GPUs.
- **FR-004**: Preserve command options, requested/effective device records, one task,
  native DDP callbacks, uploads, outputs and native training-memory cleanup.
- **FR-005**: Use the standard sequential local multirun launcher and preserve Hydra
  job environment, output/chdir behavior and normal exception propagation.
- **FR-006**: Leave historical queue state untouched and document that it is unused.

## Success Criteria

- Commands no longer create queue tickets, reservations or queued execution children.
- Busy-to-free tests start work only when enough visible GPUs are available.
- CPU, GPU and sequential multirun checks preserve task completion and exit status.
- No queue-specific cleanup exception can be emitted by the removed execution layer.

## Assumptions

- Existing GPU selectors continue to express counts; this change removes coordination,
  rather than changing selection semantics. Prediction uses one selected GPU.
- FIFO fairness and exclusive allocation between simultaneous commands are intentionally
  removed. The existing metadata-only visibility probe remains disposable.
- The earlier remote hang investigation is deferred. FiftyOne publication and SDK
  shutdown remain separate potential causes; queue removal does not prove that hang fixed.

## Amendment: configurable memory availability (2026-10-12)

This amendment changes current availability under the restored feature 024 scheduler;
the completed queue-removal history above is not a current scheduling requirement.

### User story 3 — tolerate small GPU allocations (P1)

Users can start jobs on visible GPUs with small existing allocations and customize
the cutoff in project YAML or a Hydra override without changing application code.

- **FR-007**: A GPU is free when total NVML used memory is strictly below
  `autogpu.max_used_memory_gib`, default 2.0 GiB (2048 MiB). Process presence, identity
  and utilization do not override this rule. Equality is busy.
- **FR-008**: Accept finite positive numeric limits; reject zero, negative, nonfinite,
  boolean, string and null values before admission. Existing enabled-only configs
  retain the default. Export and all model commands expose the setting.
- **FR-009**: Apply each job's limit to direct waiting and both queued modes, without
  cross-project policy leakage, reservation overlap, visibility changes or replay
  mutation. Preserve FIFO and compatible registry state.
- **FR-010**: Unknown memory telemetry fails clearly. CPU/MPS and fully disabled
  scheduling bypass probing. Owned native work must finish before contraction;
  released capacity must satisfy the same memory limit.

Acceptance: the supplied eight-card snapshot (1215, 3, 409, 3, 3, 3, 3, 3 MiB)
qualifies all cards before visibility/reservations; three visible cards can be
selected. Tests cover one byte below/equal/above the limit, custom fractional
limits, malformed telemetry/configuration and different projects sharing the queue.
