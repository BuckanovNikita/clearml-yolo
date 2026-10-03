# Research: GPU experiment queue

## Decision: user-wide local registry

Use one registry per user and operating-system instance, independent of `CY_HOME`. Resolve its
default from `XDG_STATE_HOME` or `~/.local/state/clearml-yolo/queue` on Unix-like systems and
`LOCALAPPDATA` on Windows. Accept an internal constructor root for tests without exposing a new
public configuration option.

**Rationale**: Commands launched from different workspaces must coordinate, while independent
users and operating-system instances must not accidentally share process-liveness assumptions.

**Alternatives considered**: A workspace registry misses cross-workspace collisions. A daemon or
network service expands deployment and failure scope and is explicitly excluded.

## Decision: short native-lock transactions and monotonic tickets

Guard only registry read, stale-owner reconciliation, ticket allocation, admission, transition,
release, and atomic publication with a native file lock. Never hold the lock while waiting or
running a job. Allocate monotonically increasing tickets and admit only from the live pending head;
repeat head admission while subsequent requests also fit.

**Rationale**: Short transactions serialize decisions without turning the registry lock into a
job-duration lease. Strict head-of-line FIFO is deterministic and prevents fit-based starvation.

**Alternatives considered**: Holding a file lock during execution prevents concurrent admissions
and makes crash recovery depend on lock behavior. Fit-first selection violates approved FIFO.

## Decision: supervisor-and-child native liveness locks

Give the supervisor and child separate native OS liveness locks held for their lifetimes. Reclaim
only when both locks are acquirable; never use age, TTL, heartbeat, or PID as the authority. Publish
the child lock identity under the same short registry lock before treating a reservation as fully
owned.

**Rationale**: OS lock ownership survives PID ambiguity and slow jobs. The supervisor lock closes
the spawn race and the child lock covers admitted execution.

**Alternatives considered**: Heartbeat TTL can evict a live paused process. PID/birth inspection is
platform-specific and unnecessary when native lock ownership is authoritative.

## Decision: NVML telemetry with isolated visibility mapping

Read whole-GPU inventory and active-compute-process telemetry directly through NVML. Use an isolated
metadata subprocess only to map the inherited `CUDA_VISIBLE_DEVICES` set, including ordinal and UUID
forms, to stable whole-GPU UUIDs. Treat probe errors or incomplete telemetry as unavailable capacity.

**Rationale**: The waiting supervisor and launcher must not initialize CUDA before admission.
Stable UUIDs survive child-local ordinal remapping, and fail-closed telemetry avoids reservations
based on unknown external use.

**Alternatives considered**: Importing CUDA-aware model libraries in the supervisor risks context
creation. Ordinals alone are ambiguous under inherited visibility. Memory-only checks do not prove
absence of active compute processes.

## Decision: derive demand from native device values

Normalize native training intent into a count: any nonnegative integer is one device; a list counts
its entries; every automatic `-1` entry contributes one without binding that number to a physical
GPU; null, empty, and `cuda` mean one; `cpu` and `mps` mean zero. Prediction, validation, and
comparison need one GPU when GPU-backed. A pipeline reserves `max(training_count,
gpu_inference_count)` before starting, so CPU training followed by GPU inference never reacquires.

**Rationale**: Native configuration remains the sole user-facing device contract, while scheduler
demand becomes unambiguous. Up-front maximum demand avoids mid-job deadlock.

**Alternatives considered**: A second GPU-count option can disagree with native settings. Treating
integer `2` as a count would change Ultralytics meaning. Mid-pipeline reacquisition can deadlock
several pipelines holding partial allocations.

## Decision: fresh child owns native execution and ClearML

Waiting and probing happen in a supervisor with no ClearML task and no native GPU context. After
admission, expose assigned UUIDs to a fresh child, translate the child's effective native devices
to local ordinals, and let that child own exactly one existing ClearML lifecycle. Persist requested
and effective device configurations separately.

**Rationale**: This preserves current one-task ownership and creates a clean CUDA visibility
boundary. Requested provenance remains available even though effective settings must be concrete.

**Alternatives considered**: Creating ClearML before waiting produces idle queued tasks. Running
in the supervisor cannot reliably reset inherited CUDA runtime state.

## Decision: verified pipeline contraction

After the native best model is verified and DDP cleanup is observable, confirm through telemetry
that releasable assigned UUIDs have no job compute process. Retain the first UUID, release N-1 in
one registry transaction, and run GPU prediction and comparison on child-local `0`. The first
remains reserved for CPU-only downstream work as well. The retained reservation ends with the child.

**Rationale**: Capacity returns early without releasing a GPU still used by a native worker. One
retained logical device keeps all downstream GPU work stable.

**Alternatives considered**: Releasing on training method return alone can race DDP teardown.
Monkeypatching Ultralytics cleanup violates the upstream boundary. Reacquisition risks deadlock.

## Decision: queue-aware Hydra launcher for BasicSweeper

Register `src/hydra_plugins/cy_queue/launcher.py` as the default local launcher for the five model
commands and include `hydra_plugins.cy_queue` in the wheel module list. The launcher submits all
BasicSweeper jobs FIFO, schedules admitted jobs concurrently in fresh children, preserves Hydra
callbacks, per-job environment, output directory, and chdir semantics, and returns `JobReturn`
objects in submission order. Any failed job makes the command nonzero.

**Rationale**: Hydra owns job composition and result order; the queue owns admission and process
isolation. A launcher plugin is the supported integration seam.

Hydra documents `--multirun`/`-m` and sweep parameters in its
[Multi-run guide](https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/).
Its [Submitit launcher guide](https://hydra.cc/docs/plugins/submitit_launcher/) demonstrates
selecting launcher plugins with `hydra/launcher` and overriding the launcher in defaults. This
feature supplies local GPU admission through that plugin boundary; it requires no SLURM service.

**Alternatives considered**: App-level loops lose Hydra lifecycle behavior. A custom sweeper would
duplicate BasicSweeper. In-process parallel execution cannot isolate GPU contexts.

## Dependency decision

Declare `nvidia-ml-py` directly because project code imports its NVML bindings; do not rely on the
current transitive installation. Keep `filelock` for registry locking and preserve the approved
`digital-metrics` revision.

**Rationale**: Imported runtime dependencies must be direct and lockfile-resolved.

**Alternatives considered**: Depending on a transitive package is unstable. Introducing another
GPU-management framework or changing the metrics dependency is unnecessary and out of scope.
