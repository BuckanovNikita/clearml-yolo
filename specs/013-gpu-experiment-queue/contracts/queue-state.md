# Queue state contract

## Location

The queue registry is user-wide for one operating-system instance and does not use `CY_HOME`.
Default roots are:

- Unix-like: `${XDG_STATE_HOME:-~/.local/state}/clearml-yolo/queue`
- Windows: `%LOCALAPPDATA%/clearml-yolo/queue`

An internal constructor root supports isolated tests. No public command option changes this
location, command inputs, run outputs, dependency caches, or temporary execution storage.

## Coordination

- Every submitted GPU request receives one never-reused monotonic ticket.
- Demand larger than the supported visible whole-GPU set is rejected before ticketed enqueue.
- Only the live pending head is considered for admission.
- The head receives all requested whole GPUs atomically or continues waiting.
- After admitting a head, the next live head may also be admitted when its complete demand fits.
- Reservation identity uses stable GPU UUIDs; child ordinals are derived and never own capacity.
- Registry reads that drive decisions, stale reconciliation, and writes occur under one short
  native file lock. Waiting and execution occur outside the lock.
- Durable updates use atomic replacement and validation. Unknown or corrupt state fails closed
  with an actionable error; it is not silently discarded.

## Availability and recovery

NVML must establish the full-GPU inventory and active compute users. An isolated metadata subprocess
maps inherited visibility without creating a CUDA context. Any GPU with an external compute process
is unavailable. Probe failure, incomplete telemetry, unsupported MIG visibility, or ambiguous
mapping prevents admission.

Each active request has supervisor and child native liveness locks. A reservation is reclaimed only
when both locks are acquirable. Elapsed age, TTL, heartbeat delay, and PID cannot authorize reclaim.

## Pipeline contraction

The child may contract an N-GPU reservation after verified training/model completion and
telemetry-confirmed DDP cleanup. Contraction retains the first assigned UUID and atomically releases
the others. GPU prediction and comparison use child-local device `0`. The first remains reserved
to job exit, including a CPU-only downstream phase. There is no mid-pipeline reacquisition.

Telemetry is collected outside registry transactions. Admission and contraction then reread and
validate current registry state under the lock; a concurrent change cannot be overwritten by the
pre-probe state. A driver stall can delay the probing caller but cannot block unrelated queue
registration, position, close or cleanup transactions. Active reservations have either their full
requested cardinality or one retained device after contraction; intermediate sizes are corrupt.
