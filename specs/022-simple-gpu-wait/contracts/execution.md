# GPU execution and scheduling contract

Feature 024 restores full scheduling and adds independent controls to the former
feature 022 direct-wait behavior. This maintained contract, the
[queue state contract](../../013-gpu-experiment-queue/contracts/queue-state.md) and
[runtime isolation](../../../docs/runtime-isolation.md) govern current execution.
Completed feature specifications, task ledgers and dated evidence preserve history.

## Execution controls

`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare` and `cy-export` expose validated
`queue.enabled` and `autogpu.enabled`, both defaulting to true. They are launch
controls, not workflow or native model arguments.

`autogpu.force` is a strict Boolean, default false. When true it overrides both
enabled switches: execute directly with concrete native selectors, without project
GPU discovery, NVML memory checks, queue tickets, reservations or waiting. Every
enabled GPU stage requires unique nonnegative ordinals; null, empty, `-1` and bare
`cuda` fail before native/task initialization. CPU/MPS remain supported. Parsing
ignores case and surrounding whitespace; training device order and inherited
CUDA visibility remain intact. Native backend device support still applies.
ClearML remains required; `execution_policy.force=true`, `queue=false` and
`autogpu=false` record the effective policy. Replay cannot change forced selections
(including order) through either canonical run configuration or native General.

`autogpu.max_used_memory_gib` is a finite positive numeric limit, default 2.0
GiB (2048 MiB), configurable in project YAML or a Hydra override. Existing
enabled-only configurations use that default. Booleans, strings, null, zero,
negative and nonfinite values are invalid. The limit applies to direct automatic
waiting and both queued modes, including exact selection.
Queued launch resolves the policy in the job's Hydra context and environment, then
transports concrete validated values so admission, contraction and recorded policy agree.

Phase descriptions choose device paths without importing SDKs: YOLO uses the existing
native groups; new detectors use `model.train.device` and `model.predict.device`;
export uses `export.device`. CPU/FP32 ONNX generation has zero GPU demand. Engine build
and verification require one explicit GPU selector and reject CPU. Backend validation
may reject unsupported multi-device execution without weakening scheduling guarantees.
The [multi-model contract](../../025-multi-model-backends/contracts/backend.md) preserves
all four modes below and the force override. Replay materializes typed defaults before remapping and may not
switch between initialized YOLO and new-detector runtime families.

| `queue.enabled` | `autogpu.enabled` | GPU behavior |
|---|---|---|
| true | true | FIFO admission, atomic whole-GPU UUID reservation, automatic selection and a fresh supervised execution child |
| false | true | Stateless availability wait, automatic selection and calling-process execution |
| true | false | Exact native selectors, reservation of the enabled-phase UUID union and supervised execution |
| false | false | Native device settings pass through unchanged; no project GPU discovery, availability wait or device replacement |

CPU/MPS-only and non-model commands bypass GPU scheduling. Waiting/admission occurs
before ClearML task creation and native CUDA initialization. Interrupting the wait
creates no task. Neither control disables required ClearML tracking.

## Automatic selection

GPU demand comes only from native device settings: a training integer requests one
GPU; a list or comma-separated selector requests its length; each automatic `-1`
contributes one. Null, empty or `cuda` requests one; CPU/MPS requests zero. Written
IDs express demand rather than pinned identity in automatic mode. GPU inference
requires one device; pipeline demand is the maximum of enabled training and inference
demand. There is no separate count setting or batch tuning.

NVML inventory/memory telemetry and an isolated metadata probe map inherited CUDA
visibility to whole-GPU UUIDs without initializing CUDA in the invoking process.
Required-device telemetry fails closed; visible MIG, lost visibility and requests
larger than the supported visible set fail clearly. Hidden cards with unsupported
memory telemetry or MIG do not block healthy visible cards. Exact mode checks only
the required selection; worker contraction checks its reserved devices. A GPU is free exactly when total NVML used bytes
are below `autogpu.max_used_memory_gib * 1024**3`; equality is busy. This includes
all allocations, including the invoking process and driver/graphics memory. Process
presence and utilization do not affect eligibility. Selection keeps visibility order
among eligible devices. Direct waiting creates no reservation
or fairness guarantee and simultaneous direct commands may select the same GPU.
If a pending queued request loses a visible UUID, its supervisor reports the failure
and closes its own ticket so healthy followers can advance. A follower does not remove
another live supervisor's ticket.

## Reservations and exact mode

Queued execution uses the compatible user-wide registry v1, FIFO tickets, atomic
UUID reservations, process-liveness ownership and fresh execution children. Reuse
shared state across projects. Each pending head is admitted only by its own supervisor
using its project limit; followers wait for that supervisor to poll. Active reservations
exclude devices regardless of used memory. Participating supervisors must use the
updated admission behavior for per-project limits; older versions may admit other
tickets under the old policy. Corrupt/incompatible state fails closed without
migration or deletion. Reserve only supported visible whole GPUs. Cancellation
terminates and reaps owned native descendants before releasing their capacity;
never advertise capacity while owned GPU work may remain alive.

With automatic selection disabled, queue mode requires concrete native selectors.
Resolve them against inherited visibility, reserve the UUID union of enabled
training/inference phases, and preserve requested training identity and order through
child-local remapping. Ambiguous selectors such as `-1`, null or `cuda` fail before
admission. Training and inference may select different GPUs; reserve their union.
Native memory cleanup precedes contraction; surplus devices must be below the same
launch-time memory limit. Release training-only devices and retain
the downstream inference device without changing visibility after CUDA initialization.

Requested/effective native snapshots and canonical `gpu_selection` remain separate.
Queued `gpu_selection` includes admitted `reserved_uuids`; contraction records retained
UUIDs and the inference phase under `gpu_scheduler`. ClearML replay cannot change
launch policy (including the memory limit), select identities outside the admission or exceed admitted capacity.
Invalid replay fails before native execution. The supervised child owns one task;
nested stages reuse it, while native DDP descendants do not own tasks or uploads.
Required computation, upload, flush and interruption failures remain failures.

## Hydra and launch ownership

Queued model multiruns use the distributed `hydra_plugins.cy_queue` launcher with
BasicSweeper. Submit in Hydra order; run admitted children concurrently as capacity
permits. Preserve callbacks, job environment, output directory, configured chdir,
ordered `JobReturn` results and nonzero failure outcomes. Queue-disabled multiruns
and forced multiruns use standard sequential BasicLauncher. A sweep mixing effective
queued and unqueued modes is rejected before admission, including across batches.
A force sweep can mix raw queue switches when all jobs are effectively unqueued. External/remote launchers, cross-host coordination, MIG, persistent
daemons and priority scheduling remain unsupported.

Top-level launches with `LOCAL_RANK` other than `-1` require native owner provenance
or fail before admission/task creation. Native descendants require both
`CY_CLEARML_OWNER_PID` and `CY_CLEARML_OWNER_TASK_ID`, with a different owner PID.
A rank variable alone cannot suppress task ownership.

The original remote hang remains unconfirmed. Scheduling restoration and bounded
optional-publication failures do not establish its root cause.

## Readable admission decisions

Direct and queued waits emit requested, CUDA-visible and eligible counts and the
effective memory threshold; queued decisions also include ticket and queue position.
Each physical card is explained as eligible, at/above the memory threshold, reserved
by another ticket, outside CUDA visibility or outside exact selection. Memory and
reservation reasons can appear together. FIFO blocking and insufficient eligible
capacity are separate job-level reasons; FIFO never changes an eligible card's label.

Display CUDA selector indexes (`GPU 0`); when different, include the physical index
(`GPU 0 (physical GPU 3)`). Hidden cards use physical indexes. UUIDs remain internal
for reservations and replay, and in persisted provenance rather than normal messages.
The initial decision and admission are printed, reason changes refresh at most once
every five seconds, and stable waits emit a 30-second heartbeat. Small memory changes
that do not change eligibility do not trigger messages.

Immutable admission diagnostics use the same telemetry sample and locked registry
view as admission. Sampling precedes the transaction; formatting/logging follows
lock release. `Ticket.try_acquire()` still returns a UUID tuple or None, with its
latest immutable diagnostics available separately. No second probe or position read
is needed for presentation.
