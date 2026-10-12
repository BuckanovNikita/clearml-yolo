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

Phase descriptions choose device paths without importing SDKs: YOLO uses the existing
native groups; new detectors use `model.train.device` and `model.predict.device`;
export uses `export.device`. CPU/FP32 ONNX generation has zero GPU demand. Engine build
and verification require one explicit GPU selector and reject CPU. Backend validation
may reject unsupported multi-device execution without weakening scheduling guarantees.
The [multi-model contract](../../025-multi-model-backends/contracts/backend.md) preserves
all four modes below. Replay materializes typed defaults before remapping and may not
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

NVML inventory/process telemetry and an isolated metadata probe map inherited CUDA
visibility to whole-GPU UUIDs without initializing CUDA in the invoking process.
Unknown telemetry fails closed; MIG, lost visibility and requests larger than the
supported visible set fail clearly. Only the invoking PID is ignored for direct
sequential reuse; other compute processes make a GPU busy. Selection uses visibility
order, rather than a free-memory threshold. Direct waiting creates no reservation
or fairness guarantee and simultaneous direct commands may select the same GPU.
If a pending queued request loses a visible UUID, its supervisor reports the failure
and closes its own ticket so healthy followers can advance. A follower does not remove
another live supervisor's ticket.

## Reservations and exact mode

Queued execution uses the compatible user-wide registry v1, FIFO tickets, atomic
UUID reservations, process-liveness ownership and fresh execution children. Reuse
shared state across projects; corrupt/incompatible state fails closed without
migration or deletion. Reserve only supported visible whole GPUs. Cancellation
terminates and reaps owned native descendants before releasing their capacity;
never advertise capacity while owned GPU work may remain alive.

With automatic selection disabled, queue mode requires concrete native selectors.
Resolve them against inherited visibility, reserve the UUID union of enabled
training/inference phases, and preserve requested training identity and order through
child-local remapping. Ambiguous selectors such as `-1`, null or `cuda` fail before
admission. Training and inference may select different GPUs; reserve their union.
Native memory cleanup precedes contraction; release training-only devices and retain
the downstream inference device without changing visibility after CUDA initialization.

Requested/effective native snapshots and canonical `gpu_selection` remain separate.
Queued `gpu_selection` includes admitted `reserved_uuids`; contraction records retained
UUIDs and the inference phase under `gpu_scheduler`. ClearML replay cannot change
launch policy, select identities outside the admission or exceed admitted capacity.
Invalid replay fails before native execution. The supervised child owns one task;
nested stages reuse it, while native DDP descendants do not own tasks or uploads.
Required computation, upload, flush and interruption failures remain failures.

## Hydra and launch ownership

Queued model multiruns use the distributed `hydra_plugins.cy_queue` launcher with
BasicSweeper. Submit in Hydra order; run admitted children concurrently as capacity
permits. Preserve callbacks, job environment, output directory, configured chdir,
ordered `JobReturn` results and nonzero failure outcomes. Queue-disabled multiruns
use standard sequential BasicLauncher. A sweep mixing queue modes is rejected
before admission. External/remote launchers, cross-host coordination, MIG, persistent
daemons and priority scheduling remain unsupported.

Top-level launches with `LOCAL_RANK` other than `-1` require native owner provenance
or fail before admission/task creation. Native descendants require both
`CY_CLEARML_OWNER_PID` and `CY_CLEARML_OWNER_TASK_ID`, with a different owner PID.
A rank variable alone cannot suppress task ownership.

The original remote hang remains unconfirmed. Scheduling restoration and bounded
optional-publication failures do not establish its root cause.
