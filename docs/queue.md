# Direct execution and shared queue

`cy` and stage commands run directly with native device settings. They do not import
queue implementation, inspect availability, reserve GPUs, substitute devices or wait.
`cy -m` uses sequential Hydra execution. Scheduling belongs to `cy-queue`.

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
model settings are retained. Hold the full allocation until the pipeline and all owned
descendants exit; allocation contraction is deferred. Admission defaults to total used
memory strictly below 2 GiB (`worker --max-used-memory-gib` changes it). This threshold is
separate from the capacity needed by the model/compiler.

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
streaming that file. Use `cy-queue list --json` for the full public queue view.

### Storage and scheduling

`CY_QUEUE_ROOT` selects shared durable metadata, defaulting to `$CY_HOME/.cy-queue`;
`cy-queue --root PATH` provides an explicit command override. Stable machine identity
partitions hosts; boot identity is recorded separately. Each host has its own order and
GPU capacity. `list --host HOST_ID` views another host without mutating its partition.
NFS stores atomic manifests, owner events and history. Small host-local files provide
transaction locks, worker claims and GPU UUID quarantine across queue roots and mount
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
Worker death cannot release active capacity. Cleanup uses inherited ownership markers,
PID/start-time evidence, pidfds and adopted descendants; repeated signals cannot interrupt
the bounded cleanup sequence. Only verified cleanup releases capacity.

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
90 seconds for shutdown while retaining the entire allocation. This lets the owner clean native
workers and publish final diagnostics before the guardian signals remaining
descendants. An unresponsive owner reaches the deadline and falls back to verified
whole-tree TERM/KILL cleanup. Forced termination may leave publication incomplete;
local logs and uncertain execution evidence are retained.

Guardian death or uncertain cleanup becomes `recovery_required`. The durable local claim
continues excluding its UUIDs across participating roots after OS locks disappear. Only
the owner can recover, and inaccessible or ambiguous process evidence remains blocked.
Never reclaim from a heartbeat timeout, absent parent or low GPU memory. Uncertain jobs
are never automatically retried. NFS failure stops new admission; active reservations
remain protected. Unknown protocols and damaged coordination records fail closed. The active guardian
compatibility marker identifies the queue supervision protocol; each job separately validates
its package/version/source identity. A new kernel boot establishes a fresh PID-namespace
stamp but leaves old reservations quarantined until explicit owner recovery.

Supported operation assumes cooperating Linux users, consistent NFS UID mapping and
shared host PID/local coordination namespaces. Unsupported identity/locking conditions
fail explicitly. Do not remove live coordination files. The application installs no
privileged service and changes no mounts or accounts.

## Physical GPU operator controls

These commands use **physical integer indexes in `nvidia-smi`/NVML order**, independent
of `CUDA_VISIBLE_DEVICES`. Full `GPU-...` UUIDs are also accepted. This differs from
`submit --devices` integers, which retain CUDA-visible logical order. Resolve indexes
anew after a reboot or hardware change; UUIDs identify persistent holds and claims.
Identity resolution does not need healthy memory telemetry. A full UUID can address a
stale claim even when its device is absent from inventory.

```bash
cy-queue gpu list
cy-queue gpu list --json
cy-queue gpu disable 2 --reason 'Temporarily unavailable for maintenance'
cy-queue gpu enable 2
```

`disable` persists a hold for the current Unix UID in host-local coordination. Holds
apply across queue roots and prevent new allocations; active work retains its allocation.
Any owner's hold makes a device unavailable. `enable` removes only the caller's hold,
leaving other holds and quarantine claims intact. Pending jobs report operator holds.

For an owned stale or incorrectly quarantined allocation, read its current `claim-token`
from `gpu list`. Select any one GPU from that allocation:

```bash
cy-queue gpu release 2 --claim-token TOKEN_FROM_LIST --reason 'Reviewed stale allocation'
cy-queue gpu release 2 --claim-token TOKEN_FROM_LIST --reason 'Operator accepts inaccessible stale evidence' --force
```

Normal release performs verified owned-process cleanup, like recovery. `--force` makes an
explicit audited override when stale process evidence cannot be verified; it sends no
signals. Both modes refuse a held OS lock or confirmed live guardian. Force also refuses
confirmed live owned descendants. Only the claim owner may release it, and a stale token
fails. Release covers the **whole allocation**, even when one GPU was selected. It marks
the owning job failed and preserves snapshots, history and the operator audit; it never
marks successful completion or removes holds. The claim's original queue root must be
accessible. An interrupted release can be resumed using the same selector and token.

Upgrade all cooperating workers on a host before using GPU controls. Worker startup and control mutations
install a durable compatibility fence in host coordination: old workers must reject the
unknown claim protocol instead of ignoring operator holds. Existing active allocations
remain protected and can finish. Do not delete this fence or downgrade workers while
controls are in use.

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

[Filesystem ownership](filesystem-policy.md) constrains application outputs/cache/logs/scratch
to the project. Only explicit shared queue metadata and small host-local coordination are
exceptions. SDK configuration, cache/download/temp policies and outside inputs remain intact.
[Diagnostics](diagnostics.md#live-console-and-shutdown) explains FD capture, live publication,
quiet prediction and bounded finalization. The [feature ledger](../specs/029-shared-cy-queue/tasks.md)
and dated evidence distinguish implemented behavior from physical GPU, live ClearML and
actual multi-user/multi-host NFS acceptance. CPU/mocked tests cannot substitute for those gates.
