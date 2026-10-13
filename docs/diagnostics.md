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
and cache release have separate records. DDP consumer startup/join/replay and meaningful
callback dispatch are traced without records for every empty consumer poll.

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

INFO messages describe the initial admission decision, changes in categorical reasons
(throttled to five seconds) and a 30-second waiting heartbeat. Memory fluctuations
within the same eligible/busy category do not produce new messages. Successful
admission is reported immediately.

The header shows requested, CUDA-visible and eligible device counts, the effective
`autogpu.max_used_memory_gib`, and queued ticket/position. `GPU 0` matches the
configured CUDA selector; `GPU 0 (physical GPU 3)` explains reordered visibility.
Hidden devices use their physical index. Each card reports eligibility, used memory
at/above the threshold, the reserving ticket, or exclusion by visibility/exact
selection. Memory and reservation blockers can occur together. FIFO blocking by an
earlier pending ticket is a separate line, as is insufficient eligible capacity;
FIFO does not relabel otherwise eligible cards.

Five requested GPUs with eight eligible cards and an empty queue admit immediately.
If admission waits, inspect the card reasons and FIFO line. A lower count may reflect
visibility or exact selection even when the machine has more physical cards.
Diagnostics use the admission attempt's telemetry sample and locked registry state;
formatting and logging happen after lock release. This is an observed decision,
not a guarantee that external workloads will leave capacity free after sampling.

`autogpu.force=true` bypasses these project checks and requires concrete enabled-stage
selectors. It preserves ClearML tracking and inherited visibility; it does not reserve
capacity. See the [GPU quickstart](../specs/022-simple-gpu-wait/quickstart.md).
Forced-kill orphan recovery and permission-denied process inspection are tracked
separately; the original reported waiting cause remains unconfirmed.
