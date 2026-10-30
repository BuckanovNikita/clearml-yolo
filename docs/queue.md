# Direct execution and shared queue

`cy` and stage commands run directly with native device settings. They do not import
queue implementation, perform admission, reserve GPUs, substitute devices or wait.
Explicit training `batch=null` checks hardware compatibility for saved
[batch estimation](batch-estimation.md); this is separate from queue scheduling.
`cy -m` uses sequential Hydra execution. Scheduling belongs to the separate
`cy-queue` distribution and `cy_queue` Python namespace. Dependency direction is
`cy-queue` → `clearml-yolo`; CY never imports the queue package.

The [job/reservation lifecycle diagram](queue-lifecycles.md) separates job outcomes,
process-cleanup evidence and current-generation GPU availability. The
[status map](implementation-status.md) links implementation, releases and external gaps.

## Installation

Install `clearml-yolo` from source first, including the approved external dependency
copies in [development setup](development.md#external-dependencies). Then install
`cy-queue` from its [separate public repository](https://github.com/BuckanovNikita/cy-queue)
into that same Python environment. Neither
distribution is assumed to be published on PyPI. From a CY checkout with a sibling
`cy-queue` checkout:

```bash
# Obtain the sibling checkout once if it is not already present:
git clone https://github.com/BuckanovNikita/cy-queue.git ../cy-queue
uv sync --frozen --inexact
uv pip install --python .venv/bin/python -e . -e ../cy-queue
uv pip check --python .venv/bin/python
uv run --frozen --no-sync cy-queue --help
```

The queue's package metadata declares its compatible CY range. Do not bypass that
constraint. Subsequent CY verification commands use `uv run --frozen --no-sync` in
this combined environment so synchronization does not remove the separately installed
queue. Queue-only Textual and NVML dependencies belong to `cy-queue`; shared process
supervision and lifecycle communication remain in CY. Direct commands and externally
managed ClearML Agents require neither queue installation nor queue configuration.

Installing both sources in one command refreshes editable version metadata and checks
the pair without resolving CY from an index. Before upgrading an existing shared queue,
follow the coordinated procedure below. Every release of either package requires the
[latest-pair release check](development.md#paired-cy-and-queue-release-check).

### Coordinated package upgrade

This is an offline upgrade of all cooperating queue participants:

1. Stop new submissions and all workers. Let active jobs and guardians finish, or
   perform owner cancellation/recovery and confirm no task-owned descendants or
   reservations remain. Do not remove live locks or recovery records.
2. Preserve the complete metadata and coordination trees, ownership/modes, history,
   configuration files and host bootstrap binding. Keep the existing locations and
   namespaces; extraction does not migrate or delete records.
3. Install compatible CY and cy-queue source versions in each participant's existing
   environment. Update worker service commands to use that environment consistently.
4. Read history with the new installation. Pending snapshots retain the old package
   identity and must be cancelled and resubmitted when the environment has changed.
   Preserve old records for audit; do not rewrite an identity to force execution.
5. Restart workers together after configuration and identity checks. Verify a new
   submission, ownership, cancellation and recovery using the existing coordination
   root before resuming normal work.

Do not overlap old bundled-queue workers with extracted-queue workers during the
upgrade. Configuration paths, `/tmp/clearml-yolo-queue`, lock identities and durable
record formats remain compatible; the source package move is not a coordination
relocation. Use the separate [relocation procedure](#coordination-binding-and-relocation)
only when changing a storage location deliberately.

## CY integration interfaces

The queue owns scheduling policy, durable records/storage, GPU inventory and
probing, guardians, CLI/TUI and Hydra submission composition in `cy_queue`. CY owns
shared process supervision and invocation lifecycle communication in
`clearml_yolo.adapters.runtime.process_tree` and `execution_lifecycle`. Queue integration also consumes CY's bootstrap/filesystem,
diagnostics, pure presentation/model records and Hydra configuration, validation
and sweep helpers. The [import contract](import-boundaries.md) forbids reverse
imports; both repositories test their boundary and runtime targets.

The queue composes pipeline or train, freezes the configuration, and launches the
corresponding existing CY module entrypoint. CY sends computation/publication
outcomes and training-finished messages; the queue owns durable reservations,
acknowledgement and descendant cleanup. Extraction preserves this wire protocol,
including full reservation retention when no training-finished notification arrives.
If acknowledgement is lost after durable contraction, execution stops before inference
and recovery retains the reduced claim without restoring released extra GPUs.

## Shared configuration

Every queue command except help requires a filled TOML configuration. Each user
creates `$XDG_CONFIG_HOME/clearml-yolo/queue.toml`, or
`~/.config/clearml-yolo/queue.toml` when XDG_CONFIG_HOME is unset, empty or relative.
There is no automatic config creation or implicit system-wide search. The `name`,
`root` and `coordination_root` fields are required; all users sharing a queue select
the same metadata and coordination paths:

```toml
[queue]
name = "Team training"
root = "/srv/clearml-yolo/queue"
coordination_root = "/var/lib/clearml-yolo/coordination"
# Optional in cy-queue >=0.1.6; default is 2.0 GiB:
max_used_memory_gib = 2.0
```

```bash
cy-queue config
cy-queue config --json
```

`queue.max_used_memory_gib` accepts positive finite TOML integers/floats; strings,
booleans, zero, negative and nonfinite values are rejected. It sets the existing-VRAM
admission threshold, not a reservation or model-fit guarantee. `cy-queue config`
shows the file's effective value. Restart the owned worker after changing it; existing
guardians retain the value frozen in their launch payload. Older queue readers reject
the new field, so coordinate a package upgrade before adding it to their shared file.

An explicit absolute `CY_QUEUE_CONFIG` overrides the user file. For example, an
administrator can provide one shared file, selected in every participating login
and worker-service environment:

```bash
export CY_QUEUE_CONFIG=/etc/clearml-yolo/queue.toml
cy-queue config
```

The selected file and both directory paths must be absolute. Missing or incomplete
settings fail before creating queue directories or host bindings, including with
`--root`. The metadata `root` may use NFS with consistent Unix UID mapping.
`coordination_root` uses a supported local Linux filesystem or the NFS configuration
below. It holds transaction locks, GPU reservations, worker registrations and recovery
evidence. The implementation retains files; it does not create a SQLite database.

An administrator provisions readable configuration and parent directories accessible
to every participant. For a fresh stand, shared metadata and coordination roots may
be created with sticky mode `1777`; owner directories and public records remain
owner-authored, while snapshots remain mode `0600`. Newly created queue roots use
sticky mode independently of the creator's umask. Existing root and parent modes
are preserved. Do not broaden permissions on private snapshots or project logs.
Exporting an override in one user's shell does not configure other accounts or
already-running processes. Services must select their user file or explicit override.

`cy-queue config` reads and validates settings without creating directories, acquiring
GPU locks, binding a host or starting a worker. `--json` also identifies the configuration
file and root source. `cy-queue --root /absolute/path ...` overrides only the metadata
root. Legacy `CY_QUEUE_ROOT` is accepted only if it agrees with that selected root;
otherwise remove the legacy variable or correct the configuration. There is no
project-local storage fallback. Direct training commands do not require this configuration.

### NFS coordination

Linux NFS and NFSv4 coordination mounts require effective `hard` and
`local_lock=flock` (or `local_lock=all`), with shared cache. `soft`, `softerr`,
`nosharecache` and remote/indeterminate flock settings are rejected. Inspect the
actual mount with `findmnt --target /var/lib/clearml-yolo/coordination`; the library
reads effective superblock options from `/proc/self/mountinfo`. Requested fstab
options alone may not describe the active mount, especially when multiple mounts
share an export's cache. Default NFS server-side locking does not preserve the
existing guardian's process-lifetime lock guarantee after remote lock loss.
See [Linux NFS mount semantics](https://man7.org/linux/man-pages/man5/nfs.5.html)
and [lost locks](https://man7.org/linux/man-pages/man2/fcntl_locking.2.html).

All participants on one host must share the same Linux NFS client/inode cache,
mount namespace, PID namespace and local bootstrap. Each host must have a distinct
machine identity; host-local flock does not coordinate different machines. Retain
consistent UID mapping and protected ownership/modes. Do not remount, replace or
delete the live coordination mount or files. Hard NFS may block filesystem calls
indefinitely during an outage, including status, recovery and cleanup; the transaction
contention timeout does not bound those calls. Mount-option validation is an eligibility
check, not certification of a deployment's locking, restart or outage behavior.

### Coordination binding and relocation

The fixed host bootstrap namespace under `/tmp/clearml-yolo-queue` records the selected
coordination root. All queue roots and users on the host must agree. A conflicting
configuration fails before work can reserve a second, independent set of GPU locks.
The configured location is also passed to workers and guardians; child processes do
not select a new location from their own environment.

For an existing stand, initially set `coordination_root` to its current location.
Existing legacy locks or recovery evidence prevent silently selecting another root.
There is no automatic relocation command. Relocation is an offline administrator
procedure: stop submission and all workers/guardians across participating roots,
complete owner recovery for uncertain jobs, and confirm there are no live reservations
or processes using the namespace. Preserve the complete old host directory and its
ownership/modes when copying it to the new supported coordination root. Only then atomically update
the protected bootstrap binding's canonical absolute root while retaining its protocol,
host and ownership fields; its filesystem owner must still match the recorded owner.
Update every participating configuration and restart all participants consistently. Keep the
old evidence until the move is verified. Never delete live locks or recovery records
to make a conflicting configuration pass.

## Submit and run

`submit --command pipeline` is the default and launches the existing `cy` entrypoint.
`submit --command train` launches `cy-train`; compose its own command configuration
with `cy-init-config train-config --command cy-train` and fill its required inputs.
Submission validates and freezes settings without downloading model assets. Each
job requests at least one whole GPU. Explicit CPU phases remain CPU, but they do
not create a zero-GPU queue mode; `--gpus 0` is invalid.


```bash
cy-queue submit --gpus 2 -- --config-dir cy-config --config-name cy
cy-queue submit --command train --gpus 1 -- --config-dir train-config --config-name cy-train
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

Ground-truth [dataset selectors](input-provenance.md#ground-truth-sources) are
validated and preserved in the private snapshot without downloading a dataset.
The worker resolves the selector once at execution. An omitted dataset version
uses the SDK's current selection at that time, so submission does not freeze it;
use a dataset ID or explicit project/name/version when the source must be fixed.
Resolved dataset identity, version and CSV digest are recorded separately from
the executable selector. A local CSV remains supported and warns once during
execution, not submission.

Preflight validates project request types and cross-field rules, including the supported
native parameter types and ranges, without importing model SDKs. Dataset availability,
model loading and whether the workload fits GPU memory remain execution-time checks.
Saved `hydra.sweeper.params` participate in the complete sweep. CLI task overrides take
precedence, and `hydra.mode=MULTIRUN` selects a sweep even without `-m`; `-m` overrides a
saved `hydra.mode=RUN`. Direct and queued composition share these rules. BasicSweeper
and BasicLauncher are the supported Hydra plugins; concurrency belongs to queue workers.

Each effective multirun adds one shared readable `multirun-<UTC date/time>-<word phrase>` ClearML tag
alongside each job's user-supplied `clearml.tags`. This includes one-job sweeps and
saved MULTIRUN mode. Direct launches generate a fresh group per launch; queued
submissions freeze it in every snapshot before workers execute. Repeated submissions
get different tags. Ordinary RUN leaves tags unchanged. See the
[task-grouping contract](../specs/000-baseline/spec.md#direct-execution-shared-queue-and-diagnostics).

Remove native GPU selectors from queued configurations: allocation supplies all training
devices and the first device for inference/comparison, while explicit CPU phases remain CPU.
`CUDA_VISIBLE_DEVICES` is set before the fresh pipeline process. Compilation, AMP, batch and
model settings are retained. Submission preserves explicit training `batch=null`;
the executing worker resolves it after dataset preparation against its assigned GPUs
and accessible `CY_HOME/.config/clearml-yolo/batch-estimates.json`. Estimate matching
requires the dataset vocabulary and maximum train/validation image density to fit
the synthetic bounds. Lookup prefers an exact-allocation measurement; otherwise it
uses compatible single-GPU sources for every assigned hardware type/capacity and
extrapolates `N × min(per_gpu_capacities)`. It never extrapolates across unmeasured
hardware. Origin, target allocation and source keys/status remain in provenance;
the requested null remains in replay. Submission does not estimate capacity or
replace null with a submit-host batch. A miss fails with instructions to measure
compatible idle hardware or use an explicit value. Global training batches must be
divisible by the allocated GPU count. OOM keeps normal training failure behavior;
there is no automatic retry or hidden batch reduction.
These batch-estimation/native multi-GPU interfaces describe unreleased source changes
with real multi-GPU acceptance pending.

Training holds the full allocation. After native training
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
Automatic GPU availability uses only total used VRAM strictly below
`queue.max_used_memory_gib` (default 2.0 GiB, or 2048 MiB). Equality is busy. The
worker's configured threshold is frozen into each guardian's payload and checked
again after reserving the complete allocation and immediately before workload
launch; missing telemetry or usage at/above the threshold returns
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
Readable job summaries and explicitly requested JSON results remain on stdout. Worker shutdown is reported
after orderly exit; active jobs remain supervised by their guardians. Pipeline
stdout/stderr stays in the submitting project's `.cy/queue-logs/JOB_ID.log`, with
owner-only permissions. Worker diagnostics summarize queue state rather than
streaming that file. Queue text, TUI, status logs and errors use stable references such
as `Job 17 · Training experiment`, readable host names and physical GPU indexes.
Devices absent from inventory receive collision-checked word aliases. Shortened hashes
are not display labels. Task links have readable labels; exact targets, explicit
`--json` fields and retained raw diagnostics preserve machine identities. Claim tokens
and private configuration are not included in public JSON.

### Storage and scheduling

The [shared configuration](#shared-configuration) selects durable metadata and local
coordination explicitly. Stable machine identity
partitions hosts; boot identity is recorded separately. Each host has its own order and
GPU capacity. `list --host HOST_ID` views another host without mutating its partition.
NFS stores atomic manifests, owner events and history. Small coordination files with host-local locks provide
transaction locks, generation events, worker claims and recovery records across queue roots and mount
aliases. No SQLite WAL database is placed on NFS.

Effective Unix UID and filesystem ownership govern execution. One worker per owner/root
may launch concurrent jobs with disjoint allocations. The earliest runnable job is selected:
skip owners without available workers and requests lacking a complete eligible allocation.
All participants may reorder pending local-host jobs; only owners cancel/change/recover theirs.
Running jobs cannot move or preempt. Revision checks reject stale UI/script updates.

```bash
cy-queue list --json
cy-queue move job-17 top --revision REVISION
cy-queue move job-17 before job-12 --revision REVISION
cy-queue cancel job-17
cy-queue recover job-17
```

Moves also support `up`, `down`, `bottom` and `after`. Ordering events live in each actor's
directory, so collaborators never edit another user's private files.

Job numbers come from durable submission order within the selected queue and host;
reordering changes the displayed position, not the number. Commands accept `job-17`
and compatible raw job identifiers. Names default to the configured ClearML task
name, falling back to the command; `submit --label "Training experiment"` overrides
the display name. Duplicate names remain distinguishable by job number. Submission,
mutation and GPU-control commands print human-readable text by default; use `--json`
for scripts. Listing JSON retains machine job identifiers and adds readable references.

### Unavailable task status

`cy-queue list` and the TUI refresh each owned job independently. If a private snapshot
or status cannot be read or validated, its readable public summary remains visible
with `Status unavailable; showing last recorded state`. Missing, malformed and
hash-mismatched snapshots do not hide healthy jobs or prevent their status updates.
Pending, finished and archived jobs follow the same rule; existing queue order and
archive visibility are preserved.

Text and TUI output show a warning count and identify the affected rows. Listing
JSON adds `warning_count` and `refresh_issues`, whose entries contain `job_id`,
`reference` and `message`. Both count and entries include only the selected view's
visible jobs. Messages contain no private configuration or raw validation details.
Warnings are transient: they disappear after a successful refresh and do not become
durable job errors.

Monitoring does not recover jobs, change execution outcomes or release reservations.
Viewing historical package identities and legacy configuration fields does not import
Hydra or evaluate saved pipeline overrides. Worker admission, execution and recovery
retain strict validation; being visible does not make an old snapshot executable or
migrate it. Invalid shared manifests, queue configuration and coordination failures
remain queue-wide errors. If a later TUI refresh fails this way, previously displayed
rows remain available with the error reported.

## Archive completed jobs

```bash
cy-queue archive job-17 job-18
cy-queue list --archived
cy-queue list --all --json
cy-queue restore job-17
```

Default listings and the TUI main view hide archived jobs. Only the owner may archive
or restore a job; archive accepts `completed`, `failed` and `cancelled`. Pending,
active and recovery-required jobs cannot be archived. Restoring changes visibility,
not outcome or scheduling. Repeated requests are safe and do not change the revision
when the requested flag is already present.
Text and TUI rows mark archived entries with `(archived)`, including mixed All views.
Different references to the same job count as one target in an archive confirmation.

Archive metadata is an owner-authored `archive.json` sidecar. Existing jobs without
one remain visible; public execution records, snapshots, logs and order history are
preserved. All targets are validated before any write, and each sidecar is atomically
replaced. A storage failure can leave earlier targets archived; the error is reported
and the same command can be retried. Corrupt metadata fails closed. Archive changes
participate in revision checks, while scheduling and ordering replay always use the
complete durable history. Numbers are never reused because a job was archived.
If later evidence makes a job require recovery, it reappears in the main view even
if its persisted archive flag remains set.

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

Use the same environment for submission and execution. Installation identity includes
both CY and cy-queue versions and source content, the interpreter and installed
distributions. Existing queued snapshots retain the previous identity; after an
environment change, resubmit pending jobs rather than modifying their snapshots.

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
shared host PID and coordination lock namespaces. Unsupported identity/locking conditions
fail explicitly. Do not remove live coordination files. The application installs no
privileged service and changes no mounts or accounts.

## Physical GPU operator controls

These commands use **physical integer indexes in `nvidia-smi`/NVML order**, independent
of `CUDA_VISIBLE_DEVICES`. This differs from `submit --devices` integers, which retain
CUDA-visible logical order. Resolve indexes anew after a reboot or hardware change.
Identity resolution does not require memory telemetry. Public output uses indexes or
word aliases for absent devices; displayed aliases are also valid selectors.
Previously accepted hexadecimal aliases remain compatible inputs.
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
a word-based `gpu` label and null physical index. Claims expose the job ID, owner UID and
displayed device labels. Queue-job JSON likewise uses displayed labels for requests
and allocations. Claim tokens, full UUIDs and private process/snapshot metadata are omitted.

`disable` persists a hold for the current Unix UID in host-partitioned coordination. Holds
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

There is no persistent admission bypass: every new job still checks used VRAM
strictly below its configured threshold immediately before launch. A later `disable` or a new queue reservation applies
normally. Use `cancel` or owner `recover` when process cleanup or job recovery is the intent.

Upgrade all cooperating workers on a host before using GPU controls. Worker startup and control mutations
install a durable compatibility fence in host coordination: old workers must reject the
unknown claim protocol instead of ignoring operator holds. Existing active allocations
remain protected unless explicitly freed and can finish. Do not delete this fence or
downgrade workers while controls are in use.

## Terminal UI

The `cy-queue` installation includes Textual; run `cy-queue tui` without installing
a project extra. CY alone does not install the queue UI. Textual loads only for this interface. The table shows owner, position,
state, request/allocation, waiting reason, progress and a readable ClearML task link.
Arrow keys select; `u`/`d` move, `t`/`g` send to top/bottom, and `b`/`a` select another
pending job from a dropdown for before/after ordering. `c` cancels, `r` recovers,
`x` archives, `s` restores, `v` cycles Main/Archived/All, `o` opens the task link and
`q` closes. Refresh preserves the selected row when it remains visible. Closing the
TUI leaves workers running.

## Migration and acceptance

Remove `queue.*`, `autogpu.*`, `auto_gpu.*`, `CY_GPU_QUEUE_ROOT` and the old Hydra queue launcher from
execution recipes. Regenerate saved examples with `cy-init-config`; commands reject the
old controls rather than interpreting them differently. Old queue directories and data
are preserved without automatic migration or deletion.

Follow the [coordinated package upgrade](#coordinated-package-upgrade) before replacing
the bundled queue. Record the current metadata and coordination locations and prepare
the shared TOML configuration for every user and service. Point `queue.root` at the
existing metadata to retain history. Keep its current coordination location until
the [offline relocation procedure](#coordination-binding-and-relocation) is applicable.
Add `--json` to scripts that previously consumed default machine output. Existing raw
job references remain accepted; old pending snapshots whose installation identity no
longer matches must be resubmitted. Upgrade all cooperating workers together.

Remove `worker --max-used-memory-gib` from worker commands: that flag remains invalid.
With cy-queue 0.1.6 or newer, configure `queue.max_used_memory_gib` in TOML instead;
omission retains the 2.0 GiB default. Remove `--reason`, `--claim-token` and `--force` from GPU control commands;
`gpu release INDEX` now means the same per-device manual action as `gpu free INDEX`.

[Filesystem ownership](filesystem-policy.md) constrains application outputs/cache/logs/scratch
to the project. Only explicit shared queue metadata and small host-partitioned coordination files are
exceptions. SDK configuration, cache/download/temp policies and outside inputs remain intact.
[Diagnostics](diagnostics.md#live-console-and-shutdown) explains FD capture, live publication,
quiet prediction and bounded finalization. The [feature ledger](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/029-shared-cy-queue/tasks.md)
and dated evidence distinguish implemented behavior from physical GPU, live ClearML and
actual multi-user/multi-host NFS acceptance. CPU/mocked tests do not establish those
physical outcomes. The listed unavailable external checks are
[closed by user waiver](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/docs/evidence/2026-10-16-acceptance-closure/decision.md) as
completion/release obligations; physical GPU/NFS outcomes remain unverified.

## Cross-contract integration

The [multirun grouping contract](../specs/000-baseline/spec.md#direct-execution-shared-queue-and-diagnostics) adds a
shared random ClearML tag per direct launch or queued submission. Keep the shared
Hydra tag helper, direct callback lifetime and frozen queue tags consistent. Explicit
user tags survive; ordinary RUN adds no tag.

Direct commands never schedule. Queue automatic availability uses only used VRAM
strictly below `queue.max_used_memory_gib` (default 2.0 GiB), with a fresh check
using the frozen threshold immediately before launch. Current allocations and explicit holds stay exclusive; stale
unlocked metadata alone does not veto capacity. The cutoff is independent of training
capacity. Keep [queue](queue.md), direct Hydra defaults, private snapshots, owner/guardian
adapters, CLI/TUI and README consistent.
The [operator control contract](queue.md#physical-gpu-operator-controls) uses physical
`nvidia-smi` indexes independently of CUDA visibility; submission selectors retain
their logical mapping. Queue text, JSON, TUI, status logs and errors expose physical
indexes or word aliases, with full GPU UUIDs and claim tokens kept internal.
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
earliest runnable job on each host. Shared metadata holds durable job records; coordination
files hold generations and recovery records, protected by host-local locks. Completed
historical evidence remains unchanged.
