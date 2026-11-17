# Diagnostics

Diagnostics explain what a run did and where it stopped. Every Hydra execution command
(`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth`, `cy-export`) captures its complete console output in project-local
logs, mirrors it to the terminal and publishes it to the invocation's ClearML task.
Error messages are summarized with credentials redacted. Long loops report progress, and
setting `LOGURU_LEVEL=TRACE` adds operation lifecycle records and a watchdog that shows
where a slow or stalled command is spending its time. `cy-init-config` and `cy-dedup`
also emit the TRACE command records. Diagnostics never change execution policy, timeouts,
retries, GPU use or results.

## Behavior

### Console capture

- Before configuration is composed, the command redirects file descriptors 1 and 2 to
  append-only files. The capture therefore includes Python output, native `os.write`
  output, child processes, DDP ranks, partial lines and watchdog output, with the
  original bytes unchanged.
- The files live in the invocation's runtime arena (see [filesystem](filesystem.md)):
  `<arena>/logs/stdout.log`, `stderr.log` and `scalars.jsonl` (native scalar events).
  The mirror and the publisher write their own diagnostics to
  `<arena>/logs/mirror-diagnostics.log` and
  `<arena>/logs/publisher-*/publisher-diagnostics.log`, never into the captured
  streams. The arena is retained after the command ends.
- One capture is active per process; nested commands in the same process reuse it.

### Terminal mirror

A separate local process tails the captured files and writes them to the original
terminal. It does not depend on the network, so a blocked ClearML connection cannot stall
terminal output or training. The command and its workers keep detecting whether the
original stderr was a terminal after redirection. The mirror renders opaque identifiers as
readable names, including identifiers split across writes. A terminal `tee` therefore
records the readable mirror, while the project-local capture keeps the original bytes.

The same readable rendering applies to command messages and errors, progress, DEBUG and
TRACE records, the ClearML console and display text that CY generates. A known identifier
is replaced by its name; otherwise a 32-hex task ID shows as `[task]`, a 64-hex digest as
`[checksum]`, a 40-hex revision as `[revision]`, a UUID as `[reference]`, and a plain URL
containing one as `[ClearML link]`. Rendering never changes stored identities, hashes,
cache keys, manifests, link targets or metrics; read exact identifiers from
machine-readable output or the project-local capture.

### ClearML console and scalars

- A separate publisher process attaches to the already created task; it never creates,
  closes or changes the status of a task. It sends console lines and native scalars in
  batches about every two seconds, keeps only the last carriage-return segment of each
  line and strips ANSI escape sequences.
- Published text uses readable names, like the terminal mirror. Byte offsets and
  acknowledgements are tracked against the original capture.
- Before the SDK may close or complete the task, the owner requests a publication
  barrier at the current byte offsets and waits up to eight seconds for the publisher's
  receipt. Shutdown then publishes up to the final offsets, including SDK shutdown output.
- The task deadline and the success or warning outcome that follows a publication
  failure are defined by [ClearML publication](clearml-publication.md).

### Progress reporting

- Long loops use one progress indicator. On a terminal it is a progress bar. Otherwise
  it emits a log line at most every two seconds, at steps of about a tenth of the work
  (every 100 items when the total is unknown), plus a final summary line, instead of
  rewriting a line with carriage returns.
- Prediction reports one image-count indicator per operation instead of per-image lines.
- When `CY_PROGRESS_FILE` is set, the command keeps a local JSON object there with the
  latest `progress` text, the latest training `iteration` and the task's `task_url`. The
  queue sets this variable; see [queue](queue.md).

### Error messages and redaction

- Project-handled errors are logged as an operation description, optional context and
  the exception chain (`Type: message <- Cause: message`). At INFO and above this is the
  only record. At DEBUG, which is Loguru's default, a second record adds file, line and
  function locations for every exception in the chain. Records never include source
  lines or local variables and never attach the raw exception to the sink.
- Text from messages, context and locations is redacted before emission:
  - values assigned to keys containing `access key`, `secret`, `password`, `passwd`,
    `token`, `credential`, `api key`, `authorization`, `private key`, `bearer`, `cookie`,
    `session key`, `signature` or `connection string`, or to the key `sig`, including
    whole quoted or bracketed values;
  - `Authorization`, `Proxy-Authorization`, `Cookie` and `Set-Cookie` headers and
    `Bearer` tokens;
  - every URL token with user information or a sensitive query key, replaced as a whole
    even when the URL is malformed.
- Context values under sensitive keys are never converted to text. Some opaque
  configuration payloads and failure-status fields omit the exception message entirely.
- Normal native stdout and stderr are captured raw and are not redacted. Review captured
  logs before sharing them.

### TRACE operation records

With `LOGURU_LEVEL=TRACE`, each instrumented boundary emits `START` and then `DONE`,
`FAILED` or `INTERRUPTED` through the existing Loguru sinks:

```text
START training.native.train op=2 parent=1 pid=1234 thread=5678 task=training-example elapsed=0.000s stage=train
DONE training.native.train op=2 parent=1 pid=1234 thread=5678 task=training-example elapsed=42.000s stage=train
DONE command.return op=- parent=- pid=1234 thread=5678 task=- elapsed=0.000s stage=train
```

- `op` identifies the operation within the process; `parent` is the enclosing operation
  in the same thread; `task` is the invocation task's readable name once bound, else `-`;
  `elapsed` is monotonic time since the operation started.
- Context is limited to at most 12 fields from a fixed set of scalar names (for example
  stage, split, path, destination, counts, devices and cache), with exact scalar types
  only. Text values are redacted, made readable, stripped of control characters and cut
  to 180 characters. No configuration, data frames, tensors, object representations,
  locals or source text are emitted.
- Instrumented boundaries include configuration startup and resolution, filesystem
  initialization, dataset cache locking, conversion and export, model loading, training,
  prediction and validation, evaluation, comparison, report rendering, ClearML task
  creation, download, upload, readback, flush and close, FiftyOne publication, DDP relay
  startup, join, replay and owner callback dispatch, native memory release, and cleanup.
- A `SystemExit` with status 0 is reported as `DONE`; other non-`Exception` errors are
  `INTERRUPTED`.
- `command.return` is the last record of a command, emitted after cleanup on both
  success and failure. It is not a success assertion and does not prove the process has
  exited; use the preceding terminal record and the exit status.

### TRACE watchdog

- While at least one operation is active, a daemon thread writes directly to a
  duplicate of the captured stderr descriptor, bypassing Loguru:
  - every 30 seconds, `TRACE ACTIVE` with the deepest active operation of each thread;
  - every 60 seconds, a `TRACE STACK snapshot` of Python thread locations, grouped by
    identical stacks and emitted only when the grouped snapshot changes. Threads with
    active operations come first; diagnostic threads are excluded. Output is limited to
    eight groups and 12 frames per stack, with explicit truncation lines. Frames carry
    only file name, line number and function name.
- The watchdog stops when the last operation ends, waiting at most 0.2 seconds. A forked
  child starts with fresh tracing state.

### Capturing a run for analysis

Capture both streams, because watchdog output goes only to stderr, and keep the command's
exit status (in Bash, read `PIPESTATUS` immediately after the pipeline):

```bash
LOGURU_LEVEL=TRACE cy --config-dir cy-config --config-name cy 2>&1 | tee cy-trace.log
echo "cy exit status: ${PIPESTATUS[0]}"
```

For a native compiler failure, record the command, package versions, the physical GPU
mapping, the first failed rank and the GPU memory observations. Rerunning with
`TORCHINDUCTOR_COMPILE_THREADS=1` is a supported diagnostic comparison, not an automatic
workaround; CY never sets it.

## Configuration

- `LOGURU_LEVEL`: `TRACE` enables operation records and the watchdog; `DEBUG` (Loguru's
  default) adds exception locations; `INFO` keeps short messages. Imports and tracing
  never add, remove or reconfigure sinks; an embedding application's sink must accept
  TRACE to show the lifecycle records.
- `CY_PROGRESS_FILE`: optional path, inside `CY_HOME`, for the local progress JSON.
- `CY_RUNTIME_TEMP_ROOT` selects where runtime arenas, and therefore console logs, are
  created; see [filesystem](filesystem.md).

## Failure behavior

- Local capture files survive every failure. If the terminal mirror exits abnormally, the
  command reports `Local console mirror failed; captured logs are retained`; an earlier
  computation error keeps precedence.
- A publisher that stops, writes an invalid receipt or misses its barrier or final
  offsets raises a console publication error, and the publisher process is killed.
  Uncertain deliveries are never replayed. How that error affects the command outcome is
  defined by [ClearML publication](clearml-publication.md).
- A non-finite native scalar fails with `Native scalar must be finite:` and its title,
  series, iteration and value. The rejection can expose a numerical failure already
  present in native validation; removing the scalar does not repair it. Non-finite
  losses are described in [training](training.md).
- Diagnostic emission failures never replace an application error or result. Ctrl-C and
  SIGTERM raised inside a sink still propagate, except inside mandatory cleanup spans,
  which finish their cleanup first and then raise the first interruption. If even the
  fallback error report fails, the original error is retained.
- If stderr has no usable descriptor, watchdog output is unavailable while ordinary
  lifecycle records still work.

## Limits

- TRACE intervals are sampling defaults, not deadlines. A native call holding the Python
  interpreter lock, a stopped process or blocked stderr can delay watchdog output. Stack
  snapshots show Python frames only, not native C or CUDA stacks.
- TRACE diagnoses a stall; it adds no cancellation, timeout, retry or GPU reservation.
- Watchdog output is not guaranteed to reach the ClearML console or custom Loguru sinks.
- Remote visibility latency of console and scalars is established only against a live
  ClearML server; offline and mocked runs do not establish it.

## Code and tests

- [adapters/observability/capture.py](../../src/clearml_yolo/adapters/observability/capture.py)
  and [mirror_worker.py](../../src/clearml_yolo/adapters/observability/mirror_worker.py)
  — descriptor capture, scalar journal, progress file and terminal mirror.
- [adapters/clearml/console.py](../../src/clearml_yolo/adapters/clearml/console.py) and
  [console_worker.py](../../src/clearml_yolo/adapters/clearml/console_worker.py) —
  publisher supervision, barrier and attach-only publication.
- [adapters/observability/progress.py](../../src/clearml_yolo/adapters/observability/progress.py)
  — progress indicators.
- [adapters/observability/diagnostics.py](../../src/clearml_yolo/adapters/observability/diagnostics.py)
  and [core/redaction.py](../../src/clearml_yolo/core/redaction.py) — error summaries
  and credential redaction.
- [adapters/observability/tracing.py](../../src/clearml_yolo/adapters/observability/tracing.py)
  — operation records and watchdog. Application workflows reach it through the
  execution-resource port in
  [application/ports.py](../../src/clearml_yolo/application/ports.py).
- Tests: [test_console_capture.py](../../tests/test_console_capture.py),
  [test_console_deadline.py](../../tests/test_console_deadline.py),
  [test_diagnostics.py](../../tests/test_diagnostics.py),
  [test_tracing.py](../../tests/test_tracing.py),
  [test_trace_subprocess.py](../../tests/test_trace_subprocess.py),
  [test_trace_runtime.py](../../tests/test_trace_runtime.py),
  [test_trace_clearml.py](../../tests/test_trace_clearml.py),
  [test_trace_compute.py](../../tests/test_trace_compute.py),
  [test_trace_storage.py](../../tests/test_trace_storage.py),
  [test_trace_fiftyone.py](../../tests/test_trace_fiftyone.py).
- Publication tests use an offline sink or fakes; actual ClearML console visibility is
  established only by the live suite.
