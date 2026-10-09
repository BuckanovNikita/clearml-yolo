# GPU waiting and direct execution contract

This contract supersedes the queue-specific requirements in feature 013 and the
FIFO/reservation/queued-child constitution amendment. Historical specifications,
completed tasks and dated evidence retain the former design; the
[current contract index](../../../docs/current-contracts.md) identifies current authority.

## Routing and availability

`cy`, `cy-train`, `cy-predict`, `cy-val` and `cy-compare` derive GPU demand from
native device settings. Positive demand polls supported visible whole-NVIDIA-GPU
availability before native GPU initialization and ClearML task creation. CPU/MPS
and non-model commands bypass NVIDIA inventory and proceed through their existing
invocation boundaries. Interrupting the wait creates no ClearML task.

NVML inventory and compute-process telemetry fail closed when unavailable or
unsupported. The isolated metadata-only GPU probe maps inherited CUDA visibility
to stable whole-GPU UUIDs without initializing the invoking process's CUDA context.
Unsupported MIG, lost visibility and demand exceeding the supported visible set
fail clearly instead of waiting indefinitely. A GPU with another compute process is
busy; only the invoking PID is ignored so sequential jobs can reuse their own
retained CUDA context. This is process availability, not a free-memory threshold.

When enough GPUs are available, select logical indices in inherited visibility
order. Do not rewrite `CUDA_VISIBLE_DEVICES`. A metadata probe and native Ultralytics
DDP descendants can be subprocesses; model workflows execute in the calling process.
Waiting uses no queue registry, tickets, reservation, liveness locks or job supervisor.
There is no FIFO fairness, concurrency control or exclusive allocation guarantee:
simultaneous commands can observe and select the same free GPU.

## Demand and effective settings

| Native training device intent | GPU demand |
|---|---:|
| nonnegative integer such as `2` | 1 |
| list such as `[0,1]` | 2 |
| automatic integer/list entry `-1` | 1 per entry |
| comma-separated GPU selectors | Number of entries |
| null, empty string, or `cuda` | 1 |
| `cpu` or supported `mps` selector | 0 |

Written GPU identifiers express a count rather than pinning physical devices.
GPU-backed prediction, validation and comparison require one GPU. Pipeline demand
is the maximum of enabled training demand and enabled downstream inference demand;
there is no separate count setting. Native training receives the selected logical
indices required by its demand. GPU inference receives the first selected logical
index, which need not be `0`. Explicit CPU/MPS settings remain CPU/MPS.

Native training-memory cleanup remains between training and downstream work and
after GPU invocations. It releases model allocations; no scheduler reservation or
capacity-contraction step exists.

## Provenance, tracking and failures

Requested configuration stays separate from translated effective configuration.
Training retains `ultralytics_requested.yaml`; prediction retains
`ultralytics_predict[_<index>]_requested.yaml` alongside effective YAML. Comparison
retains its role/split requested snapshots. Canonical run configuration records
`gpu_selection` with `selected_devices`, `requested_devices` and `effective_devices`;
there are no reserved UUIDs or scheduler phases. Selected devices are logical indices
within inherited visibility. ClearML replay cannot increase demand beyond the
availability selection made before task creation; reject such a replay before native
execution.

Each invocation owns one ClearML task. Preserve native callbacks, requested/effective
records, artifact/model publication, outputs, failure reporting and completion.
Nested stages reuse the invocation; native DDP descendants do not own tasks or uploads.
Workflow exceptions propagate directly without conversion to worker exit receipts
or queue-cleanup exceptions. Existing native cleanup and task finalization still apply.

## Hydra and launch ownership

Local multiruns use Hydra's standard sequential BasicLauncher with BasicSweeper.
Preserve callbacks, job environment, per-job output directory, configured chdir,
ordered job results and normal failure propagation. Each job waits and executes in
the launcher process. No project launcher plugin or queued worker is distributed.

Top-level launches with `LOCAL_RANK` other than `-1` require native owner provenance;
otherwise reject them before task creation. External rank-bearing launchers remain
unsupported. Recognize native descendants through both `CY_CLEARML_OWNER_PID` and
`CY_CLEARML_OWNER_TASK_ID`, with the owner PID different from the current process.
A generic rank variable alone cannot suppress invocation ownership.

Historical queue directories are untouched and unused. No migration, deletion or
replacement coordination service is part of this change. The former remote hang
investigation remains deferred; queue removal does not establish that SDK shutdown
or FiftyOne publication hangs are fixed.
