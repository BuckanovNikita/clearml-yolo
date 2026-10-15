# Direct execution and shared queue

`cy` and stage commands run directly with native device settings. They do not import
queue implementation, inspect availability, reserve GPUs, substitute devices or wait.
`cy -m` uses sequential Hydra execution. Scheduling belongs to `cy-queue`.

The [job/reservation lifecycle diagram](queue-lifecycles.md) separates job outcomes,
process-cleanup evidence and current-generation GPU availability. The
[status map](implementation-status.md) links implementation, releases and external gaps.

## Submit and run

```bash
cy-queue submit --gpus 2 -- --config-dir cy-config --config-name cy
cy-queue submit --devices 0,2 -- --config-dir cy-config --config-name cy
cy-queue submit --gpus 1 -- -m --config-dir cy-config --config-name cy ultralytics.epochs=10,20
cy-queue worker
cy-queue list --json
```

Count and exact-device requests are mutually exclusive. Submission integer selectors use
CUDA-visible logical order, including `CUDA_VISIBLE_DEVICES` remapping, and resolve to
ordered physical UUIDs at submission. The entire sweep is composed and validated before
any job is committed. Submission returns stable IDs. Owner-private immutable snapshots
retain resolved settings, project/cwd, interpreter, installed package/environment identity
and resources. Workers revalidate identity before execution; changed installations require
resubmission. Credentials come from the owning user's environment. Public summaries never
contain executable configurations.

Preflight validates project request types and cross-field rules, including the supported
native parameter types and ranges, without importing model SDKs. Dataset availability,
model loading and whether the workload fits GPU memory remain execution-time checks.
Saved `hydra.sweeper.params` participate in the complete sweep. CLI task overrides take
precedence, and `hydra.mode=MULTIRUN` selects a sweep even without `-m`; `-m` overrides a
saved `hydra.mode=RUN`. Direct and queued composition share these rules. BasicSweeper
and BasicLauncher are the supported Hydra plugins; concurrency belongs to queue workers.

Each effective multirun adds one shared random `multirun-<UUID4 hex>` ClearML tag
alongside each job's user-supplied `clearml.tags`. This includes one-job sweeps and
saved MULTIRUN mode. Direct launches generate a fresh group per launch; queued
submissions freeze it in every snapshot before workers execute. Repeated submissions
get different tags. Ordinary RUN leaves tags unchanged. See the
[task-grouping contract](../specs/030-multirun-tags/contracts/tags.md).

Remove native GPU selectors from queued configurations: allocation supplies all training
devices and the first device for inference/comparison, while explicit CPU phases remain CPU.
`CUDA_VISIBLE_DEVICES` is set before the fresh pipeline process. Compilation, AMP, batch and
model settings are retained. Training holds the full allocation. After native training
returns and releases unused model memory, the job notifies its external guardian and
waits for a bounded acknowledgement. The guardian first durably shrinks the claim to
the first allocated GPU, then releases the other GPU locks and updates the public
allocation before acknowledging. Other jobs may use those released GPUs during
inference/comparison; normal memory admission still applies. The retained first GPU
remains reserved until the pipeline and its owned descendants exit, unless explicitly
freed. A job that sends no
training-finished notification retains its full allocation. Once a valid notification
has durably shrunk the claim, later record-write or acknowledgement failure does not
restore released GPUs. A failed or unacknowledged handoff stops the pipeline before
inference; cleanup/recovery follows the remaining durable claim. This is not successful
pipeline completion.
Automatic GPU availability uses only total used VRAM strictly below 2 GiB (2048 MiB).
Exactly 2 GiB is busy. This fixed limit is checked again after reserving the complete
allocation and immediately before workload launch; missing or higher telemetry returns
the attempted job to pending and releases its reservation. Process lists and utilization
do not determine availability. Current queue allocations and explicit operator holds
remain exclusive until released; stale unlocked bookkeeping alone does not exclude a GPU.
The admission limit is separate from the capacity needed by the model/compiler.

## Shared ownership and ordering

### Worker diagnostics

`cy-queue worker` writes INFO diagnostics to stderr by default: startup queue root,
host, owner UID and memory threshold; changed owner-job states, GPU allocations,
waiting reasons, progress and errors; and a heartbeat every 60 seconds. An empty
queue reports `idle` immediately. Unchanged jobs are not repeated on each poll,
and completed history is counted without replaying old completion messages.
Failed jobs and jobs requiring recovery are reported at ERROR level.

```bash
cy-queue worker --log-level DEBUG
cy-queue worker --log-level WARNING
```

DEBUG adds a summary for every poll; WARNING or ERROR suppress routine INFO output.
Job IDs and JSON command results remain on stdout. Worker shutdown is reported
after orderly exit; active jobs remain supervised by their guardians. Pipeline
stdout/stderr stays in the submitting project's `.cy/queue-logs/JOB_ID.log`, with
owner-only permissions. Worker diagnostics summarize queue state rather than
streaming that file. Use `cy-queue list --json` for the public queue view. Queue text,
JSON, TUI, status logs and errors show physical GPU indexes, with short unambiguous
labels for devices absent from inventory. Full GPU UUIDs and claim tokens remain internal.

### Storage and scheduling

`CY_QUEUE_ROOT` selects shared durable metadata, defaulting to `$CY_HOME/.cy-queue`;
`cy-queue --root PATH` provides an explicit command override. Stable machine identity
partitions hosts; boot identity is recorded separately. Each host has its own order and
GPU capacity. `list --host HOST_ID` views another host without mutating its partition.
NFS stores atomic manifests, owner events and history. Small host-local files provide
transaction locks, generation events, worker claims and recovery records across queue roots and mount
aliases. No SQLite WAL database is placed on NFS.

Effective Unix UID and filesystem ownership govern execution. One worker per owner/root
may launch concurrent jobs with disjoint allocations. The earliest runnable job is selected:
skip owners without available workers and requests lacking a complete eligible allocation.
All participants may reorder pending local-host jobs; only owners cancel/change/recover theirs.
Running jobs cannot move or preempt. Revision checks reject stale UI/script updates.

```bash
cy-queue list --json
cy-queue move JOB_ID top --revision REVISION
cy-queue move JOB_ID before OTHER_JOB_ID --revision REVISION
cy-queue cancel JOB_ID
cy-queue recover JOB_ID
```

Moves also support `up`, `down`, `bottom` and `after`. Ordering events live in each actor's
directory, so collaborators never edit another user's private files.

## Guardians, cancellation and recovery

Each execution has a same-user Linux subreaper guardian. It records its identity and claim
before opening the native launch gate and owns GPU locks independently of the worker.
Worker death cannot release active capacity. The guardian owns descendant cleanup outside
the job's ClearML finalization. Live discovery follows its own child topology across
threads, recorded process births and subreaper adoption, with PID/start-time checks
and pidfds. An unrelated same-UID process whose `/proc` environment is inaccessible
does not invalidate this scoped supervision. Repeated signals cannot interrupt bounded
cleanup. The acknowledged training handoff releases only extra GPUs; ordinary guardian
release follows verified cleanup. Explicit [manual freeing](#physical-gpu-operator-controls)
independently clears the selected device's reservation without stopping its workload.

A successful computation with required uploads can complete its ClearML task before
the guardian finishes cleanup. Later supervisor uncertainty reports `recovery_required`
and retains cleanup evidence; current reservations remain exclusive, while stale unlocked
metadata does not veto automatic admission. It does not retroactively fail that successful task.
Computation and mandatory publication failures still fail the task. A completed task
or local artifacts alone do not prove that queue capacity is safe to reclaim.

Worker registration, the snapshot's Python interpreter and guardian startup all check
Linux process supervision before admission or native launch. A Python build missing
`os.pidfd_open`, `signal.pidfd_send_signal` or other required APIs fails with the
interpreter path and missing capability. Unsupported kernel pidfd operations also fail.
Use a compatible Linux Python/kernel environment and resubmit if installation identity
changed; there is no unsafe cleanup fallback. These checks prevent a long training run
from discovering an unsupported API only during validation or shutdown.

The package accepts Python `>=3.12.13,<3.14`; that version range does not guarantee
the required APIs were compiled into the interpreter. Older standalone Python builds
can omit them even on a modern kernel. Update the interpreter distribution or choose
a compatible build, then run its actual capability probe before submitting work:

```bash
python -c 'from clearml_yolo.adapters.runtime.process_tree import require_process_supervision; require_process_supervision()'
```

Use the same environment for submission and execution. Existing queued snapshots
retain the previous interpreter and installation identity and may need resubmission.

Normal cancellation first signals the verified pipeline owner and allows up to
90 seconds for shutdown while retaining the current allocation. This lets the owner clean native
workers and publish final diagnostics before the guardian signals remaining
descendants. An unresponsive owner reaches the deadline and falls back to verified
whole-tree TERM/KILL cleanup. Forced termination may leave publication incomplete;
local logs and uncertain execution evidence are retained.

Guardian death or uncertain cleanup becomes `recovery_required`. Durable local records
retain the uncertain outcome. Current reservations exclude their devices across
participating roots; stale unlocked records alone do not block new admission. Only
the owner can recover the job. Recovery performs conservative global ownership discovery;
inaccessible or ambiguous process evidence remains blocked, even though unrelated
processes do not poison the live guardian's scoped tree.
Heartbeat expiry, absent parents and low GPU memory do not prove process cleanup or a
successful job outcome. Explicit manual freeing requires no cleanup proof. Uncertain jobs
are never automatically retried. NFS failure stops new job admission; active reservations
remain protected. Unknown protocols and damaged coordination records fail closed. The active guardian
compatibility marker identifies the queue supervision protocol; each job separately validates
its package/version/source identity. A new kernel boot establishes a fresh PID-namespace
stamp; prior outcome records remain available for owner recovery without making stale,
unlocked metadata an automatic capacity veto.

Supported operation assumes cooperating Linux users, consistent NFS UID mapping and
shared host PID/local coordination namespaces. Unsupported identity/locking conditions
fail explicitly. Do not remove live coordination files. The application installs no
privileged service and changes no mounts or accounts.

## Physical GPU operator controls

These commands use **physical integer indexes in `nvidia-smi`/NVML order**, independent
of `CUDA_VISIBLE_DEVICES`. This differs from `submit --devices` integers, which retain
CUDA-visible logical order. Resolve indexes anew after a reboot or hardware change.
Identity resolution does not require memory telemetry. Public output uses indexes or
short unambiguous absent-device labels; displayed short labels are also valid selectors.
Full UUIDs stay in internal coordination records.

```bash
cy-queue gpu list
cy-queue gpu list --json
cy-queue gpu disable 2
cy-queue gpu enable 2
cy-queue gpu free 2
cy-queue gpu release 2
```

GPU JSON rows expose `gpu`, `physical_index`, `holds` and `claim`; an absent device has
a short `gpu` label and null physical index. Claims expose the job ID, owner UID and
displayed device labels. Queue-job JSON likewise uses displayed labels for requests
and allocations. Claim tokens, full UUIDs and private process/snapshot metadata are omitted.

`disable` persists a hold for the current Unix UID in host-local coordination. Holds
apply across queue roots and prevent new allocations; active work retains its allocation.
Any owner's current hold makes a device unavailable. `enable` removes only the caller's
hold; `free` clears every existing hold and reservation for the selected GPU across roots.
Pending jobs report operator holds.

`free` and `release` are equivalent. They accept the user's declaration immediately,
without tokens, reasons, force flags, confirmation, memory/process checks or signals.
They clear **only the selected GPU**, including its live reservation and existing holds;
other GPUs in the same allocation remain reserved. The original queue directory need
not be accessible. Repeated freeing succeeds. Operator events are recorded automatically
without deleting another owner's private files.

Freeing advances that GPU's reservation generation under the host transaction. Older
locks and claim/hold records no longer block it. Earlier guardians cannot recreate its
released reservation, overwrite a newer one, or clear a newer allocation during handoff,
recovery or cleanup. Existing processes continue, and their job outcomes remain independent
of freeing capacity. `free` does not cancel a job or declare it completed or failed.

There is no persistent admission bypass: every new job still checks used VRAM below
2048 MiB immediately before launch. A later `disable` or a new queue reservation applies
normally. Use `cancel` or owner `recover` when process cleanup or job recovery is the intent.

Upgrade all cooperating workers on a host before using GPU controls. Worker startup and control mutations
install a durable compatibility fence in host coordination: old workers must reject the
unknown claim protocol instead of ignoring operator holds. Existing active allocations
remain protected unless explicitly freed and can finish. Do not delete this fence or
downgrade workers while controls are in use.

## Optional terminal UI

Install `clearml-yolo[queue-ui]` or use `uv sync --dev --extra queue-ui --inexact`, then
run `cy-queue tui`. Textual loads only for this interface. The table shows owner, position,
state, request/allocation, waiting reason, progress and ClearML link. Arrow keys select;
`u`/`d` move, `t`/`g` send to top/bottom, `b`/`a` move before/after an entered ID, `c`
cancels, `r` recovers and `q` closes. Closing the TUI leaves workers running.

## Migration and acceptance

Remove `queue.*`, `autogpu.*`, `auto_gpu.*`, `CY_GPU_QUEUE_ROOT` and the old Hydra queue launcher from
execution recipes. Regenerate saved examples with `cy-init-config`; commands reject the
old controls rather than interpreting them differently. Old queue directories and data
are preserved without automatic migration or deletion.

Remove `worker --max-used-memory-gib` from worker commands: admission now uses the fixed
2 GiB limit. Remove `--reason`, `--claim-token` and `--force` from GPU control commands;
`gpu release INDEX` now means the same per-device manual action as `gpu free INDEX`.

[Filesystem ownership](filesystem-policy.md) constrains application outputs/cache/logs/scratch
to the project. Only explicit shared queue metadata and small host-local coordination are
exceptions. SDK configuration, cache/download/temp policies and outside inputs remain intact.
[Diagnostics](diagnostics.md#live-console-and-shutdown) explains FD capture, live publication,
quiet prediction and bounded finalization. The [feature ledger](../specs/029-shared-cy-queue/tasks.md)
and dated evidence distinguish implemented behavior from physical GPU, live ClearML and
actual multi-user/multi-host NFS acceptance. CPU/mocked tests cannot substitute for those gates.

## Cross-contract integration

The [multirun grouping contract](../specs/030-multirun-tags/contracts/tags.md) adds a
shared random ClearML tag per direct launch or queued submission. Keep the shared
Hydra tag helper, direct callback lifetime and frozen queue tags consistent. Explicit
user tags survive; ordinary RUN adds no tag.

Direct commands never schedule. Queue automatic availability uses only used VRAM strictly
below 2 GiB (2048 MiB), with fresh admission checks immediately before launch and no
configurable threshold. Current allocations and explicit holds stay exclusive; stale
unlocked metadata alone does not veto capacity. The cutoff is independent of training
capacity. Keep [queue](queue.md), direct Hydra defaults, private snapshots, owner/guardian
adapters, CLI/TUI and README consistent.
The [operator control contract](queue.md#physical-gpu-operator-controls) uses physical
`nvidia-smi` indexes independently of CUDA visibility; submission selectors retain
their logical mapping. Queue text, JSON, TUI, status logs and errors expose physical
indexes or short absent-device labels, with full GPU UUIDs and claim tokens kept internal.
Per-owner holds exclude new host allocations across roots. `gpu disable INDEX`,
`enable INDEX`, `free INDEX` and its `release INDEX` alias need no supplementary
arguments. Manual freeing clears only that GPU's existing reservations and holds without
memory/process checks, signals, original queue access or changing the job outcome.
Per-device generations fence earlier guardians and preserve sibling reservations; the
next job still needs fresh memory admission. Keep capability preflight, hold/claim
transactions and remote
[GPU DDP acceptance](ddp-testing.md) aligned with these rules.

Feature 029 replaces the historical four-mode execution policy with direct commands and
`cy-queue`. Old switches fail with migration guidance. Training holds the complete
allocation until acknowledged contraction; the first device remains reserved through
descendant exit unless explicitly freed. Guardian death retains an uncertain job outcome
for owner recovery, without letting stale unlocked records block new admission. Ordering selects the
earliest runnable job on each host. NFS holds durable records, host-local coordination
holds locks, generations and recovery records. Completed historical evidence remains unchanged.
