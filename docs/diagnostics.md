# Diagnosing a slow or stalled command

Set `LOGURU_LEVEL=TRACE` before starting an execution command to enable operation
lifecycle records and the process watchdog. Without this opt-in, the existing DEBUG
(default) or INFO diagnostics remain; operation tracing starts no watchdog.
TRACE changes diagnostic visibility, not execution policy, timeout, retries or results.

## Capture a run

Use your existing configuration and a writable log destination. This Bash script
captures both native output and project diagnostics while preserving the command's
exit status, including when `set -e` is active:

```bash
#!/usr/bin/env bash
set -euo pipefail
if LOGURU_LEVEL=TRACE cy --config-dir cy-config --config-name cy 2>&1 | tee cy-trace.log; then
    trace_status=("${PIPESTATUS[@]}")
else
    trace_status=("${PIPESTATUS[@]}")
fi
exit "${trace_status[0]}"
```

Run this as a script: its final `exit` terminates that script. `PIPESTATUS` is captured
immediately in both branches before another command can overwrite it. The same pattern
works with `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth`, `cy-init-config` and `cy-dedup`, using their own arguments.
Raw native stdout/stderr retain their existing behavior; the combined log is not a
redacted export of those streams.

## Read the records

Illustrative project records, with the caller's Loguru prefix omitted:

```text
START training.native.train op=2 parent=1 pid=1234 thread=5678 task=task-id elapsed=0.000s stage=train
TRACE ACTIVE training.native.train op=2 parent=1 pid=1234 thread=5678 task=task-id elapsed=30.000s parent_stage=workflow.train stage=train
DONE training.native.train op=2 parent=1 pid=1234 thread=5678 task=task-id elapsed=42.000s stage=train
DONE command.return op=- parent=- pid=1234 thread=5678 task=- elapsed=0.000s stage=train
```

Operation records contain `START`, then `DONE`, `FAILED` or `INTERRUPTED` as the boundary
finishes. `op` identifies an operation within the process, `parent` identifies its enclosing
operation in the same thread, and `pid`/`thread` identify its execution context. `task` is
the invocation-owned ClearML task when bound, otherwise `-`; `elapsed` is monotonic time
since that operation began. Selected scalar context may include stage, split, artifact,
path or destination, row/image/class counts, devices, and cache hit/miss information.
Context is bounded to 12 permitted scalar fields, with redacted text values capped at
180 characters. Values are summaries, not configuration or data dumps.

Coverage follows blocking boundaries: configuration discovery/resolution and composition,
GPU discovery/wait/selection, dataset cache locking/conversion/export, native model load,
training/prediction/validation, evaluation/calibration/matching/AP, comparison cache and
significance, report rendering, ClearML initialization/download/upload/readback/flush,
optional FiftyOne publication, and cleanup. Native memory collection, CUDA synchronization
and cache release have separate records. DDP relay startup/join/replay and owner callback dispatch are traced. The background
consumer only parses local records and emits no SDK effects or late lifecycle spans.

Every 30 seconds while operations remain active, the watchdog reports the deepest active
operation in each traced thread. Every 60 seconds it samples Python thread locations,
groups identical stacks and emits a snapshot only when that grouped snapshot changes.
Active operation threads are considered first; diagnostic threads are excluded. Output is
limited to eight groups and 12 frames per stack, with explicit truncation notices. Stack
frames contain only filenames, line numbers and function names; snapshots do not read
locals or source excerpts and do not format exception tracebacks.

A pending operation without a terminal record identifies the last entered boundary.
Repeated `TRACE ACTIVE` records show where elapsed time accumulates; stack changes can
show movement between Python calls. A completed computation may still be followed by
artifact upload, model verification, flush, task closure, DDP join or native-memory cleanup.
`command.return` marks the final instrumented command boundary after cleanup, including
failure paths; it does not by itself indicate success or prove the process has exited.
Use the preceding terminal record and captured command exit status to determine success.

## Output ownership and limits

Ordinary operation lifecycle records use existing Loguru sinks. Imports and tracing do
not remove, replace or reconfigure caller-owned sinks; an embedding application's sink
must accept TRACE to display those records. The watchdog alone writes directly to a
captured duplicate of stderr, bypassing Loguru and its locks for heartbeats and stack
snapshots. Capture stderr as shown above; watchdog output is not guaranteed to appear in
the ClearML Console or a custom Loguru sink. If stderr has no usable file descriptor,
watchdog writes may be unavailable while ordinary lifecycle records still work.

The monitor is a daemon thread, stops when the last active operation finishes, and has
bounded shutdown waiting. Ordinary diagnostic exceptions preserve application results.
Termination exceptions (KeyboardInterrupt/SystemExit, including signal handlers) propagate
during normal emission so Ctrl-C and SIGTERM retain their effect. An already-active
application exception takes precedence over logging failures in nested finalization spans.
Mandatory cleanup spans defer interruptions raised during diagnostic emission until their
cleanup body finishes, then propagate the first interruption. Nested cleanup spans share
that boundary; interruptions in actual application/native work retain their usual behavior.
Tracing does not install or replace signal handlers.
A stalled native call that holds Python's interpreter lock, a stopped process, or blocked
stderr can delay output: the 30/60-second intervals are sampling defaults, not execution
deadlines. Thread locations describe Python boundaries rather than native C/CUDA stacks.
Tracing diagnoses a stall; it does not unblock SDK/native work or add cancellation,
timeouts, retries, GPU reservations or allocation guarantees. Independent execution
controls and bounded FiftyOne workers are defined by [runtime isolation](runtime-isolation.md);
those features do not make TRACE itself a deadline or establish the original hang cause.

Project-generated context and locations use the existing credential redaction policy.
They omit full configurations, argument dumps, DataFrame contents, image inventories,
tensors, arbitrary SDK object representations, locals and source text. Normal native
stdout/stderr forwarding remains raw. Review the captured log before sharing it.

## Dependency boundaries

The [observability adapter](../src/clearml_yolo/adapters/observability/tracing.py) owns the
watchdog and lifecycle mechanics. Application workflows request tracing through the
[execution resource port](../src/clearml_yolo/application/ports.py), supplied by
[CLI composition](../src/clearml_yolo/entrypoints/composition.py), rather than importing
adapter logging internals. Evaluation and FiftyOne adapters may depend on observability
for diagnostics; scientific core records and algorithms remain independent of it.

## GPU admission decisions

Direct commands do not perform GPU admission. `cy-queue list --json` and the TUI expose
pending order, owner UID, requested resources, allocation and the current wait reason.
Admission selects the earliest runnable job using its owner's available worker and full
GPU set. Automatic availability uses only used VRAM strictly below 2 GiB (2048 MiB),
including a fresh check immediately before launch; equality is busy. The limit is fixed.
Current reservations and explicit holds exclude capacity regardless of low memory;
stale unlocked records alone do not. Queue text, JSON, TUI, status logs and errors use
physical GPU indexes or short absent-device labels, never full GPU UUIDs or claim tokens.
A free device does not prove that the selected compiled model/batch fits.

For a stuck job inspect its owner worker and guardian state. `recovery_required` means
cleanup or outcome is uncertain; owner `cy-queue recover ID` must prove descendant cleanup.
To declare physical GPU 2 free, use `cy-queue gpu free 2` (or `gpu release 2`). It clears
only that device's current reservations and holds, requires no token/reason/force flag,
and performs no memory/process check or signals. Existing processes and job outcomes
remain unchanged; the next job still needs fresh memory admission. Never delete live
lock files or use age/PID disappearance alone as cleanup proof. Capture native
compiler errors with command, package versions, physical mapping, first failed rank and
memory observations. `TORCHINDUCTOR_COMPILE_THREADS=1` is a supported diagnostic comparison,
not an automatic workaround. See [queue operations](queue.md).

## Live console and shutdown

Project FD capture retains stdout.log, stderr.log and scalar records in invocation scratch.
It includes Python, os.write/native output, DDP children, partial lines and watchdog output.
Terminal mirroring runs independently of the network; the publisher writes diagnostics to
its own local stream. Console carriage-return progress is coalesced; prediction normally
emits one operation progress indicator and summary instead of per-image lines.

The attach-only publisher batches approximately every two seconds. Healthy-service
acceptance requires console and produced epoch scalars visible remotely within ten seconds
while training remains active. A mocked/offline run does not prove this latency. Shutdown
uses final offsets and a deadline, retains local logs, and fails incomplete required
publication without retrying uncertain deliveries. Original computation errors take
precedence over cleanup failures, including a configured Loguru sink or stderr failing
while reporting that cleanup. Memory-cleanup failures and interruptions propagate when
there is no earlier error. Required owner finalization has a 60-second Unix
main-thread deadline covering publication and SDK close, which performs its own second
drain. An existing embedding alarm is rejected without overwriting it.
An unconfirmed initialization or shutdown also blocks later same-process task
creation, including remaining sequential sweep members, to prevent reuse of a
failed SDK owner. Inspect the first error and relaunch remaining work in a fresh
process; no private SDK state is reset automatically.

## Cross-contract integration

`LOGURU_LEVEL=TRACE` enables the maintained [operation diagnostic contract](diagnostics.md):
lifecycle records preserve caller Loguru sinks; a separate watchdog writes 30-second
per-thread deepest-operation heartbeats and 60-second changed grouped location-only
stacks to captured stderr, bounded to eight groups and 12 frames. Scalar context is
redacted and bounded; full configuration/data/locals/source dumps are excluded.
Application workflows access tracing through the execution-resource port; evaluation
and FiftyOne adapters may depend on observability. Keep operation coverage and this
guide current when blocking boundaries change. Cleanup and `command.return` are
observable without altering execution, retry, timeout or GPU allocation policy.
