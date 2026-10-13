# Queue state contract

> Feature 024 restores the compatible queue protocol described here and amends it
> with independent execution controls and exact device selection. The maintained
> [GPU execution contract](../../022-simple-gpu-wait/contracts/execution.md) defines
> the four modes, replay and cancellation rules. Completed feature history is preserved.

## Location

The queue registry is user-wide for one operating-system instance and does not use `CY_HOME`.
Capture the inherited user-wide state root before project XDG overrides. Default roots are:

- Unix-like: `${XDG_STATE_HOME:-~/.local/state}/clearml-yolo/queue`
- Windows: `%LOCALAPPDATA%/clearml-yolo/queue`

An internal constructor root supports isolated tests. No public command option changes this
location, command inputs, run outputs, dependency caches, or temporary execution storage.

## Coordination

- Every submitted GPU request receives one never-reused monotonic ticket.
- Demand larger than the supported visible whole-GPU set is rejected before ticketed enqueue.
- Only the live pending head is considered for admission, by its own supervisor.
- The head receives all requested whole GPUs atomically or continues waiting.
- After admitting a head, the next live head can be admitted on its supervisor's next poll
  when its complete demand fits. Each supervisor uses its own project memory limit.
- Reservation identity uses stable GPU UUIDs; child ordinals are derived and never own capacity.
- Registry reads that drive decisions, stale reconciliation, and writes occur under one short
  native file lock. Waiting and execution occur outside the lock.
- Durable updates use atomic replacement and validation. Unknown or corrupt state fails closed
  with an actionable error; it is not silently discarded.

## Availability and recovery

NVML must establish the full-GPU inventory and total used memory. An isolated metadata
subprocess maps inherited visibility without creating a CUDA context. Admission uses
the project memory limit defined in the [execution contract](../../022-simple-gpu-wait/contracts/execution.md);
process presence alone does not make a GPU unavailable. Active queue reservations
always exclude their devices. Probe failure, incomplete required-device telemetry, unsupported MIG
visibility or ambiguous mapping prevents admission. Hidden or exact-selection-excluded
cards do not block admission on healthy required GPUs. Registry v1 is retained; use
updated supervisors together because older versions can admit other projects' tickets.

Each active request has supervisor and child native liveness locks. A reservation is reclaimed only
when both locks are acquirable. Elapsed age, TTL, heartbeat delay, and PID cannot authorize reclaim.

## Pipeline contraction

The child may contract an N-GPU reservation after verified training/model completion and
owned native/DDP cleanup and telemetry confirming surplus GPUs are below the launch
memory limit. Memory telemetry alone does not prove descendant cleanup. The worker
uses the same configured limit as its supervisor. Contraction retains the first assigned UUID and atomically releases
the others. GPU prediction and comparison use child-local device `0`. The first remains reserved
to job exit, including a CPU-only downstream phase. There is no mid-pipeline reacquisition.

Telemetry is collected outside registry transactions. Admission and contraction then reread and
validate current registry state under the lock; a concurrent change cannot be overwritten by the
pre-probe state. A driver stall can delay the probing caller but cannot block unrelated queue
registration, position, close or cleanup transactions. Active reservations have either their full
requested cardinality or one retained device after contraction; intermediate sizes are corrupt.

## Decision evidence and force bypass

A ticket exposes immutable diagnostics from its latest admission attempt without
changing the return contract of `try_acquire()`. One telemetry sample is joined with
active ticket owners and pending order inside the admission transaction. Format and
log only after releasing the registry lock; do not re-read queue position or telemetry
to explain that attempt. CUDA logical/physical indexes are display metadata; registry
v1 still stores UUIDs and is unchanged.

`autogpu.force=true` bypasses the queue entirely and preserves concrete native device
choices. It neither reads nor modifies existing tickets and does not reserve capacity.
Forced-kill orphan recovery and permission-denied process inspection are separate
follow-ups; this change does not claim to resolve either lifecycle issue.
