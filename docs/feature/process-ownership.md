# Process ownership

Every CY execution command is the owner of the processes it starts. A direct command
(`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth`, `cy-export`) runs with its native device settings, without queue
admission, GPU reservation, waiting or device substitution. On Linux it tracks every
process it launches, including detached ranks, forked data workers and orphans of exited
workers, and before it returns it terminates and verifies the exit of those processes,
whether the command succeeded, failed or was cancelled. It never signals processes it
cannot prove it owns. Native multi-GPU training ranks and `cy-batch-estimate` cases use
the same supervision. Commands launched by `cy-queue` hand process cleanup to the queue
guardian instead; see [queue](queue.md).

## Behavior

### Direct execution

- Native `device` settings reach the backend unchanged. `cy -m` runs sweep members one
  after another in the same process with Hydra's basic launcher; concurrency belongs to
  the queue.
- The command holds no GPU reservation. When the workflow ends, the owner releases unused
  native GPU memory before the ClearML task is completed. A failure of that release is
  logged and never replaces an earlier error; without an earlier error it fails the
  command.

### Ownership scope

After the invocation's ClearML task exists, the workflow runs inside one ownership scope.
The scope:

1. checks process-supervision support (see Failure behavior);
2. makes the command process a Linux child subreaper, so descendants whose parent exits
   are reparented to it instead of to init;
3. records every Python fork made inside the scope and marks launched descendants with a
   private per-invocation environment marker;
4. treats processes that already existed when the scope started, such as the terminal
   mirror and the console publisher, and their descendants as protected helpers.

A process is owned when it is a new descendant of the command found through the child
lists of all its threads, an adopted orphan, a recorded fork, or a marked process. Every
process is tracked as a PID together with its kernel start time, so a reused PID is never
taken for an owned process. Signals are delivered through pidfds after the identity is
rechecked. Unrelated processes of the same user are not scanned and cannot block cleanup.

### Cleanup

When the scope ends for any reason, the command:

1. sends SIGTERM to every owned process, descendants before their direct parent;
2. after two seconds, sends SIGKILL to anything still owned and running;
3. requires two consecutive scans that find no owned process and no topology change, so
   a late fork cannot slip between scans;
4. gives up after ten seconds in total and reports the failure;
5. reaps recorded zombie children of its own, restores the previous subreaper setting
   and removes the marker.

A forked child that unwinds the scope never performs this cleanup; only the original
command process does.

### Supervised workers

- Native multi-GPU training ranks and batch-estimation trials run as fresh worker
  processes, each in its own session with its own marker and log file. The command
  returns only after every worker and all of its descendants have exited. A nonzero exit
  of any rank, or the trial deadline, terminates all peers immediately; the caller sees
  `success`, `crash` or `timeout` with the exit codes.
- Independent batch-estimation cases each own only their own descendants. A finished or
  failed case is cleaned without stopping its peers. A case whose cleanup cannot be
  verified is reported once, keeps its slot unusable and is retried when the pool closes.
- Nested supervisors keep every ancestor's marker, so a detached grandchild remains
  attributable after it is reparented.

### Cancellation and signals

- Ctrl-C raises an interruption and SIGTERM ends the command with exit status 143
  (128 + 15); both unwind through the ownership scope and run the cleanup above.
- During cleanup, SIGINT and SIGTERM are deferred. Repeated signals do not interrupt it.
  After cleanup the first deferred signal is delivered to the previous handler, unless an
  error is already being raised, which then takes precedence.

## Configuration

Process ownership has no user settings. The owner markers are internal environment
variables and must not be set by users. Saved or command-line `queue.*`, `autogpu.*` or
`auto_gpu.*` settings and `hydra/launcher=cy_queue` are rejected before execution:

```text
Legacy queue/autogpu controls are removed from direct cy commands. Remove these settings
from CLI overrides and saved YAML. Use cy-queue submit for scheduled execution; direct
commands preserve native devices.
```

To check an interpreter before starting long work, run its actual capability probe:

```bash
python -c 'from clearml_yolo.adapters.runtime.process_tree import require_process_supervision; require_process_supervision()'
```

## Failure behavior

- On Linux, missing support fails before any model work, naming the interpreter:
  `Process supervision unavailable in …: missing os.pidfd_open, …`, a failed kernel
  `pidfd_open`, `pidfd_send_signal` or `waitid(P_PIDFD)` probe, a failed subreaper probe,
  or `Process supervision cannot read /proc identity in …`. There is no fallback to
  PID-only signalling. On other platforms the capability probe fails with
  `Process supervision requires Linux: …`.
- If owned processes survive the ten-second bound, cleanup fails with
  `Owned descendants survived bounded cleanup`.
- If `/proc` denies access to a relevant descendant, cleanup fails with
  `Cannot verify model process cleanup: /proc access denied for PIDs […]` and that
  process is not signalled.
- If protected helpers exist and an adopted child has neither a marker nor a fork
  record, its origin is ambiguous: it is left untouched and cleanup fails with
  `Cannot prove native ownership of adopted children with preexisting helper branches`.
- A cleanup failure never hides the workflow's own error: both are raised together as
  `Native execution, descendant cleanup or restoration failed`. Worker groups keep the
  workflow error as well: rank groups raise `Worker execution and cleanup failed` (or
  `Training worker cleanup failed` when cleanup alone failed), and batch-estimation pools
  raise `Independent worker cleanup failed`.
- A worker deadline must be finite and positive; otherwise no worker starts.

## Limits

- Supervision exists only on Linux. On other platforms the ownership scope does nothing
  and launched processes are not tracked or cleaned.
- The Python version range does not guarantee the pidfd APIs; some standalone Python
  builds omit them even on a current kernel.
- The marker is launch provenance, not a security boundary against malicious processes
  of the same user. Marker contents are never logged.
- Heartbeat loss, a missing parent or low GPU memory never count as proof that
  descendants exited.
- Cleanup of real DDP ranks on physical multi-GPU hosts is established only on that
  hardware; ordinary tests use real CPU processes.

## Code and tests

- [adapters/runtime/process_tree.py](../../src/clearml_yolo/adapters/runtime/process_tree.py)
  — capability checks, ownership discovery, bounded cleanup and signal deferral.
- [adapters/runtime/workers.py](../../src/clearml_yolo/adapters/runtime/workers.py) and
  [worker_pool.py](../../src/clearml_yolo/adapters/runtime/worker_pool.py) — supervised
  rank groups and independent case pools.
- [entrypoints/hydra/common.py](../../src/clearml_yolo/entrypoints/hydra/common.py) —
  where direct commands enter the ownership scope and release GPU memory.
- [entrypoints/hydra/validation.py](../../src/clearml_yolo/entrypoints/hydra/validation.py)
  — rejection of legacy scheduling controls.
- Tests: [test_direct_execution.py](../../tests/test_direct_execution.py),
  [test_direct_descendants.py](../../tests/test_direct_descendants.py),
  [test_subreaper_process_tree.py](../../tests/test_subreaper_process_tree.py),
  [test_process_capabilities.py](../../tests/test_process_capabilities.py),
  [test_gpu_cancellation.py](../../tests/test_gpu_cancellation.py),
  [test_training_workers.py](../../tests/test_training_workers.py),
  [test_worker_pool.py](../../tests/test_worker_pool.py),
  [test_nested_worker_cleanup.py](../../tests/test_nested_worker_cleanup.py),
  [test_execution_controls.py](../../tests/test_execution_controls.py),
  [test_gpu_force.py](../../tests/test_gpu_force.py).
- These tests use real Linux processes on CPU. Cleanup of DDP ranks on physical
  multi-GPU hosts is established only by native runs on that hardware.
