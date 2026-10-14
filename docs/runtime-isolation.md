# Controlled execution and runtime ownership

[Direct execution and shared queue](queue.md) governs current execution controls and
guardians. [Filesystem ownership](filesystem-policy.md) defines project containment and
retained scratch. Feature 024 and older GPU specifications remain historical records.

## Selected configuration export

`cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]` accepts `cy`, `cy-train`,
`cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth` and `cy-export`.
The default is `cy`. Each invocation writes exactly one `<command>.yaml` wrapper.
The five existing model commands default to YOLO and also write `ultralytics/default.yaml`
and `ultralytics_predict/default.yaml`. A new-detector selection instead writes
`model/<backend>/<preset>.yaml`; `cy-export` defaults to `fasterrcnn/resnet50_fpn` and accepts
only Faster R-CNN. Metrics, report and ground-truth commands require no model group files.
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
sequential. Replay rejects switching between initialized YOLO and new-detector families.

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
Linux subreaper guardian which owns GPU locks throughout the whole pipeline. Worker exit
does not release those locks. Repeated SIGINT/SIGTERM defers interruption during bounded
TERM/KILL descendant cleanup. PID/start-time checks, inherited markers, pidfds and adopted
children protect against PID reuse and detached ranks. Unknown or inaccessible ownership
blocks ordinary release. Guardian death leaves durable quarantine; owner `cy-queue recover ID`
releases it after proven cleanup. The explicit audited
[GPU operator controls](queue.md#physical-gpu-operator-controls) additionally permit
owner-only whole-allocation release with a current claim token; force sends no signals
and refuses live locks or positively identified living owners/descendants.
No heartbeat expiry, missing parent or low GPU-memory
observation establishes cleanup. Marked supervised jobs discover new ownership from
the inherited marker, never a numeric parent/session relationship alone. Retained
identities are refreshed before use. Empty discovery must remain stable across two
scans; disappearing entries or changed identities require another bounded attempt.
Environment-access denial is cleared only after confirming process exit, while
living or unverifiable candidates continue to block release. Old cancellation work
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
uses a 60-second Unix main-thread deadline for required uploads, flush, readback and
close. The budget includes both the explicit flush and the SDK's own close-time
drain; publisher receipt waits retain their separate shorter bound. Incompatible
embedding timers fail explicitly.
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
