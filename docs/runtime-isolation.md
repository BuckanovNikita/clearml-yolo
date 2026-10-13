# Controlled execution and runtime ownership

The [feature 024 specification](../specs/024-runtime-isolation/spec.md) and
[GPU execution contract](../specs/022-simple-gpu-wait/contracts/execution.md) govern
execution controls and supervised workers. [Filesystem ownership](filesystem-policy.md)
defines project paths and retained scratch. Dated evidence records its original behavior;
the current boundary preserves normal library configuration and cache discovery.

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
|---|---:|---|
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
training, so workers do not require persisted settings or import-time mutations.

New detectors use `detector_runtime()` after admission with the same project scratch and
ClearML finalization boundaries. RF-DETR and Roboflow retain their own configuration and
cache defaults. DEIM uses the verified private source loader and restores ambient
pycocotools module identities around upstream import/dataset construction. Concurrent
detector families require separate processes because the DEIM module alias boundary is
sequential. Replay rejects switching between initialized YOLO and new-detector families.

Shared GPU coordination remains user-wide and outside invocation scratch. Compatible
registry state coordinates projects; incompatible or corrupt state fails closed without
migration or deletion. Owned process cleanup remains mandatory before releasing GPU
capacity. Retaining scratch does not establish successful descendant cleanup or publication.

During supervised shutdown, additional SIGINT/SIGTERM signals are deferred until
bounded cleanup finishes; prior handlers are restored and cancellation still reports
failure. On Linux, a private inherited launch marker and process start identities
identify native children even when Torch starts ranks in separate sessions or their
launcher exits first. Cleanup signals confirmed identities through Linux pidfds and
requires two stable empty descendant scans before releasing capacity. An exit or fork
that invalidates discovery triggers another bounded cleanup iteration; failure to
establish stable emptiness remains an error. Linux requires pidfd
support and readable `/proc` state. Recovering already-orphaned ranks also requires
environment visibility for same-user processes created since the worker started.
An unrelated newer non-dumpable process can therefore prevent verified cleanup:
confirmed job processes are terminated, but unknown ownership remains an error.
Inaccessible state never proves a process exited. Environment contents are not logged.
Native children must retain the inherited marker for discovery. Supervised jobs use
this provenance and retained process identities, never numeric parent/session
relationships alone. The private compatibility path without a launch marker retains
its older ancestry/session fallback and cannot provide the same PID-reuse guarantee.
Windows retains Job Object cleanup; other POSIX systems retain process-group cleanup.
This does not provide recovery after forcibly killing the supervisor itself.

Stop a job with `Ctrl+C` in its original terminal and wait for cleanup to finish.
For an existing stranded ticket, inspect that ticket's supervisor/worker lock owners
on the machine running the job and stop the identified invocation. Do not remove
registry or lock files while their owners are alive: deleting files neither stops
GPU work nor safely releases its reservation.
