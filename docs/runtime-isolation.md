# Controlled execution and runtime ownership

[Direct execution and shared queue](queue.md) governs current execution controls and
guardians. [Filesystem ownership](filesystem-policy.md) defines project containment and
retained scratch. Feature 024 and older GPU specifications remain historical records.

## Selected configuration export

`cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]` accepts `cy`, `cy-train`,
`cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth` and `cy-export`.
The default is `cy`. Each invocation writes one `<command>.yaml` wrapper and its
local command base: for example, `cy.yaml` includes `pipeline.yaml`, while
`cy-train.yaml` includes `train.yaml`. Public YAML and private `_cy_schemas`
ConfigStore names are distinct, avoiding automatic schema matching. Fresh exports
include the application YAML dependency closure; legacy trees can still resolve
packaged public defaults without rewriting. Local files, interpolation, CLI overrides,
multirun and explicit validation retain their precedence and behavior.
The five existing model commands default to YOLO and also write `ultralytics/default.yaml`
and `ultralytics_predict/default.yaml`. A new-detector selection instead writes
`model/<backend>/<preset>.yaml`; `cy-export` defaults to `fasterrcnn/resnet50_fpn` and accepts
only Faster R-CNN. Training exports include both augmentation profiles and selected
model/profile specializations. Metrics, report and ground-truth commands require no
model group files, but still receive their local base.
Only selected destinations and their parents participate in overwrite preflight.
Unrelated files remain unchanged. Existing selected files fail without `--force`;
force replaces regular files only, never symlinks or directories. No ClearML task
or native model runtime is created for export.

```bash
cy-init-config cy-config
cy-init-config metrics-config --command cy-metrics
cy-metrics --config-dir metrics-config --config-name cy-metrics --help
```

Back up custom YAML before regenerating each command; see
[configuration migration](python-import-migration.md#regenerate-saved-configuration).
`dump_config_tree(directory, *, command="cy", model=None, overwrite=False)` exposes the same
selection for Python callers.

## Optional FiftyOne operations

FiftyOne remains enabled by default where publication is supported. Factory,
preflight, request preparation, publication, local receipt and run-link failures
warn and preserve otherwise successful computation and the ClearML task.
`fiftyone.enabled=false` selects a dependency-free no-op publisher. Cancellation
retains interruption semantics.

| Setting | Default seconds | Scope |
| --- | ---: | --- |
| `fiftyone.preflight_timeout_seconds` | 60 | Setup operation, including import and worker exit |
| `fiftyone.publish_timeout_seconds` | 900 | Publication operation, including import and worker exit |
| `fiftyone.lock_timeout_seconds` | 30 | Database publication lock acquisition |

Overrides must be finite and strictly positive. Each operation uses a fresh
supervised subprocess with no GPU visibility, queue lease or ClearML task ownership.
The supervisor drains diagnostics, waits for successful exit and validates operation
and task identity plus a complete receipt before reporting success. A receipt from
a failed or timed-out worker cannot establish publication success. Termination
allows up to five seconds for graceful cleanup and five for forced reaping; unsafe
cleanup is reported explicitly. Partial persistent database state is retained for
same-task retry. Publication never installs the App plugin automatically.

```bash
cy --config-dir cy-config --config-name cy fiftyone.preflight_timeout_seconds=30 fiftyone.publish_timeout_seconds=300 fiftyone.lock_timeout_seconds=10
```

This containment does not establish the root cause of the original remote hang.
Fault injection verifies bounded failure behavior independently of that incident.

## Runtime boundary

Execution commands and `cy-init-config` initialize project paths through a stdlib-only
bootstrap. `cy-dedup` initializes no application directories or SDKs and removes its own
atomic temporary siblings beside the selected destination. Package imports remain inert.
The runtime scope covers execution, descendants, optional publication, required uploads
and task finalization. `command.return` follows process/task cleanup and is not a success
assertion; invocation scratch remains available after that boundary.

`CY_HOME` controls project outputs and the CSV dataset cache. `CY_RUNTIME_TEMP_ROOT`
selects the parent of invocation arenas, defaulting to `CY_HOME/.tmp`. Project temporary
callsites pass the arena explicitly. `TMPDIR`, `TMP`, `TEMP`, global `tempfile` defaults
and bytecode settings are unchanged. Unique arenas are retained after success, errors,
interruption and cancellation. Startup performs no scratch scans or abandoned recovery;
no scope recursively deletes an arena. Delayed children and overlapping invocations may
still use retained files. Deliberate maintenance requires confirming that the relevant
workspace and all descendants are idle.

Libraries retain normal environment, user settings, cwd configuration discovery, caches
and credential-provider behavior. Selectors outside `CY_HOME` remain valid and unchanged.
SDK imports use normal cwd and SDK constants; the project does not create config
placeholders or bind later workspace selection to an SDK root. SDKs may retain their own
imported settings, independently of changes to `CY_HOME`. Existing earlier project-local
settings/caches remain on disk; reuse them through explicit supported SDK selectors as
shown in [filesystem ownership](filesystem-policy.md#reuse-earlier-project-local-library-paths).

`native_runtime()` also supplies retained scratch for programmatic use and reuses an outer
CLI arena. Its ClearML setting and callback changes are in memory only and restore on
exit without writing the Ultralytics settings file. The invocation owner remains the only
tracking owner. Fresh DDP trainers scope callback ownership during construction and
training, so workers do not require persisted settings or import-time mutations. Rank zero
appends live scalars to the invocation journal; the relay consumer parses local event
records without SDK callbacks. Installed callbacks replay synchronously in the owner
under a deadline, suppressing scalar duplicates already sent through the journal.

New detectors use `detector_runtime()` during direct execution with the same project scratch and
ClearML finalization boundaries. RF-DETR and Roboflow retain their own configuration and
cache defaults. DEIM uses the verified private source loader and restores ambient
pycocotools module identities around upstream import/dataset construction. Concurrent
detector families require separate processes because the DEIM module alias boundary is
sequential. Agent replay restores its backend before either runtime is initialized.

## Native training workers

The native multi-GPU implementation, available from 0.41.0, keeps the invocation owner outside
distributed ranks. Supervised fresh workers receive typed requests, report typed
results and never own ClearML publication. A rank failure, timeout or cancellation
terminates the owned group before another trial starts. Rank zero owns aggregate
metrics and unwrapped checkpoints; the invocation owner records selected batch
provenance and publishes the experiment. Estimation also uses fresh supervised
workers with exactly one GPU per trial, observes that GPU's memory and leaves unrelated
workloads intact. Multi-GPU batch recommendations are extrapolated from compatible
single-GPU evidence. Physical DDP training acceptance remains a separate gate; see
[batch estimation](batch-estimation.md).

## ClearML Agent execution

CY supports its existing recorded `pipeline` and `train` module entrypoints under
an externally managed ClearML Agent. The ClearML adapter reads one detached replay
snapshot before mandatory-input validation and backend selection. The selected
runtime initializes, then the existing invocation lifecycle joins the same task.
Remote script metadata, task ownership, required publication, failure reporting and
cleanup remain owned by that lifecycle.

A missing canonical `run` object may use complete explicit launch arguments. A
present empty or malformed canonical object fails instead of silently selecting
local defaults. Canonical settings and supported scientific General overrides keep
the existing precedence; observed General values do not override native detector
`model` settings. Original output ownership and task identity are preserved.

Agent-provided `CUDA_VISIBLE_DEVICES` and configured native logical device settings
remain unchanged. No queue package, configuration or reservation is required.
Explicit training `batch=null` inspects the assigned hardware to resolve a saved
[batch estimate](batch-estimation.md), without queue admission. Dependencies are
installed by the Agent's environment; CY does not install
them at execution time and introduces no separate task-submission interface.

Non-YOLO assets resolve only after canonical inputs are recorded and only in an
execution copy. `run` retains explicit selectors and null defaults; resolved paths,
source URLs and hashes are recorded in a separate `model_assets` Configuration
Object and do not replace canonical replay inputs. Help, configuration inspection and
queue submission perform no asset resolution. See [model assets](model-assets.md).

### Git workspace warning

The nine experiment commands listed in the [command contract](../specs/000-baseline/spec.md#commands-and-configuration)
inspect the original launch cwd once inside console capture and before Hydra can
change directories. This includes help/config inspection and emits at most one
workspace warning per invocation, including multiruns. The warning uses stderr
and existing captured logs; stdout and workload exit semantics are preserved.
It recommends a Git checkout or deliberate `git init` for versioning experiment
configuration, without initializing or modifying a repository.

The read-only Git probe has a five-second timeout and ignores inherited `GIT_*`
overrides. Repository roots, subdirectories, unborn repositories, linked worktrees
and submodules are accepted. Bare repositories, missing Git, unsuccessful or
unrecognized responses and OS/timeout failures produce an advisory warning that
membership could not be verified. A verification failure does not prove absence.
The check is independent of CY_HOME, tracked files, cleanliness, remotes and
ClearML's package-source identity. Config export, deduplication, queue administration
and direct programmatic workflow calls do not perform this check. A queued
pipeline process checks its recorded launch cwd through the ordinary entrypoint.
See [regression coverage](../tests/test_git_workspace.py).

## Cancellation and recovery

On Linux, native execution checks required Python APIs, pidfd kernel operations,
subreaper access and its `/proc` identity before entering the native scope. A missing
`os.pidfd_open` is an actionable startup error naming the interpreter. Queue workers
also probe the frozen job interpreter before changing its pending state, and guardians
check again before reserving devices. Unsupported environments fail before model work;
they do not substitute PID-only signalling for identity-safe cleanup.

Direct commands do not acquire queue resources. A native invocation scope marks and
cleans newly launched Linux descendants using ancestry, subreaper adoption and Python
fork birth records while preserving pre-existing helper branches and any inherited
guardian marker. A newly adopted unmarked child with ambiguous origin is left untouched
and reported as unverifiable cleanup; missing provenance never authorizes a signal. Queued commands use a separate same-user
Linux subreaper guardian which owns process cleanup outside ClearML task finalization.
The job only sends an opaque training-finished notification after native training
returns and unused model memory is released; it imports no queue GPU-management code.
The guardian durably retains the first GPU, releases extra GPU locks and updates
queue allocation before acknowledging. Unless explicitly freed, the first GPU remains
reserved through pipeline/descendant exit; absent a training-finished notification, the full allocation
remains reserved. Failure after durable contraction can leave extras released even
without acknowledgement; cleanup/recovery uses the remaining durable claim.
Worker exit does not release active locks. Repeated SIGINT/SIGTERM defers interruption during bounded
TERM/KILL descendant cleanup. PID/start-time checks, inherited markers, pidfds and adopted
children protect against PID reuse and detached ranks. Unknown or inaccessible ownership
blocks ordinary cleanup. Guardian death leaves durable recovery evidence; owner `cy-queue recover ID`
settles it after proven cleanup. Stale unlocked records alone do not prevent automatic
GPU admission. The
[GPU operator controls](queue.md#physical-gpu-operator-controls) additionally permit
`gpu free INDEX` or `gpu release INDEX` to clear only the selected physical GPU's
reservations and existing holds immediately. They require no tokens, reasons, force
flags, confirmation, memory/process checks or access to the original queue root and
send no signals. Existing processes, sibling reservations and job outcomes remain
unchanged. Per-device generations prevent older guardian writes, training handoff,
recovery and cleanup from restoring a freed reservation or affecting a newer allocation.
Every new job still needs used VRAM below 2 GiB immediately before launch.
No heartbeat expiry, missing parent or low GPU-memory observation establishes cleanup.
Live guardians follow only their own child topology across threads, recorded births
and subreaper adoption; unrelated same-UID `/proc` access denials cannot poison that
scoped tree. Recovery retains conservative global marker discovery. There, environment
access denial is cleared only after confirming process exit, and living or unverifiable
candidates block owner recovery. Retained identities are refreshed before use; empty discovery
must remain stable across two scans, with churn requiring another bounded attempt.
A completed successful ClearML task is not retroactively failed by subsequent guardian
cleanup uncertainty: the queue reports `recovery_required` and retains recovery evidence.
Current allocations stay exclusive unless explicitly freed; stale unlocked records alone
do not veto capacity.
Required computation/upload failures retain their failure semantics. Old cancellation work
is retained in generic process supervision and guardian regression tests; forced
termination is covered separately.
Normal queue cancellation gives the verified pipeline owner up to 90 seconds to
clean native workers and finish publication before the guardian applies its final
descendant TERM/KILL barrier. New descendant identities remain recorded during
that grace period, and repeated cancellation does not reset the deadline.

## Console capture and publication

FD-level append-only logs capture Python/native/DDP stdout/stderr beneath the project.
A network-independent mirror preserves terminal output and saved terminal capability.
An attach-only publisher batches console/scalar events for the existing task and owns no
lifecycle transitions. Diagnostics use a separate local file to prevent feedback loops.
An acknowledged workload checkpoint precedes SDK close/completion. Final offsets include
SDK shutdown output and a finite deadline governs publisher shutdown; uncertain delivery is not
automatically replayed. Required publication failure fails the run and retains its logs,
while cleanup preserves the original computation exception. The owner task finalization
uses a 10-minute (600-second) Unix main-thread deadline for required uploads, flush,
readback and close in both direct and queued runs. The budget includes both the
explicit flush and the SDK's own close-time drain; publisher receipt waits retain
their separate shorter bound. Incompatible embedding timers fail explicitly.
Separate failure cleanup and console/status handling use the same 10-minute owner
deadline per scope; this is not a total queue-job or total process-exit timeout.
If task initialization or owner shutdown cannot complete, later invocations in that
process fail before creating or reusing a ClearML task. This includes later members
of a sequential Hydra sweep. Relaunch them in a fresh process after inspecting the
original failure; the adapter does not reset the SDK singleton or replay uncertain
deliveries. A normally closed owner permits the next sequential invocation.
Failure cleanup stops that owner's status monitor before marking failure, so the
SDK cannot treat the application's own transition as an external abort. Incomplete
closure detaches only the owner's task/reporter exit callbacks and bounds closure
of its cached logging handler. Other SDK owners, handlers and configuration remain
outside that cleanup. The original safe error diagnostic precedes the publication
barrier; full local logs retain the outer traceback as well.
See [diagnostics](diagnostics.md) and dated acceptance evidence for actual remote visibility.

## Cross-contract integration

[Runtime isolation](runtime-isolation.md) defines selected export (default only `cy`),
finite FiftyOne worker deadlines and receipt validation. The stdlib bootstrap runs before
SDK imports to initialize project paths, preserving normal library configuration/cache
selectors and global temporary defaults. Explicit project temporary callsites use retained
invocation arenas; startup performs no recovery scan or recursive arena cleanup.
[Filesystem ownership](filesystem-policy.md) defines outputs, cache locks, idle maintenance
and explicit opt-in to earlier local SDK paths. Native ClearML callback switches are scoped
in memory and restored without persisting settings, including fresh DDP trainers.
The original remote hang is unconfirmed; containment does not establish its cause.
