# Bug assessment: batch-estimate error diagnostics drop telemetry evidence

- Date: 2026-11-07
- Slug: `estimate-error-diagnostics` (generated)
- Source: secondary defects 1–3 of the
  [selected-L telemetry assessment](../selected-l-telemetry-loss/assessment.md#secondary-diagnosability-defects-confirmed-not-root-cause)
  (repository evidence, no URL).
- Verdict: valid; low severity. Measurements still fail closed; only the recorded
  evidence of the failure is lost.

## Symptom

When native batch estimation loses GPU telemetry, the saved catalogue cannot explain
why. Three code-level defects combine:

1. `application/use_cases/batch_estimate.py` `_measure` records
   `f"{type(error).__name__}: {error}"`. For an `ExceptionGroup` this keeps only
   `"ExceptionGroup: ... (2 sub-exceptions)"` and drops every leaf, such as the
   nvidia-smi `CalledProcessError`, the cleanup `TimeoutExpired` and the
   surviving-descendant `RuntimeError`.
2. `adapters/integrations/batch_probe.py` `NativeBatchProbe.run` catches only
   `FileNotFoundError` and `RuntimeError`. The `run_workers` group
   ("Worker execution and cleanup failed") escapes, so the failed attempt is never
   observed as a trial and the case keeps `trials: []`. Inspection found the same gap
   for a lone `CalledProcessError` or `TimeoutExpired`: when cleanup succeeds,
   `run_workers` re-raises the monitor's primary failure unwrapped, and it is not a
   `RuntimeError`.
3. `adapters/runtime/gpu_inventory.py` `_query` uses `check=True`. The
   `CalledProcessError` and `TimeoutExpired` texts omit nvidia-smi's stdout and
   stderr, where NVML prints its error (for example "Failed to initialize NVML:
   Generic operating system error").

Expected: the failed trial is recorded with its status. The diagnostic shows every
leaf failure and the nvidia-smi output. Existing status classification is unchanged.

## Reproduction

CPU-only and deterministic; new regressions construct the conditions:

1. Make `run_workers` raise
   `BaseExceptionGroup("Worker execution and cleanup failed", [CalledProcessError, TimeoutExpired])`
   from `NativeBatchProbe.run`, and run `estimate_batches` with a raising probe.
2. Make a fake `nvidia-smi` executable on `PATH` print NVML text and exit 12, then
   call `gpu_inventory.gpu_states()`.

## Root cause

The diagnostics were written for single exceptions; the probe's handler predates
`run_workers` returning grouped and non-`RuntimeError` telemetry failures. Confidence
is high from code inspection and the three native reproductions in the source
assessment.

## Remediation

- Add a pure `error_diagnostic(error)` to `core/batch_estimation.py`. It renders
  `Type: message` (unchanged for an ordinary exception without notes), appends
  `__notes__`, and recursively lists group leaves by using the group's `message`
  instead of its counted `str()`.
- `_measure` uses it for both failed-preparation and failed-trial diagnostics.
- `NativeBatchProbe.run` adds a branch after the unchanged `RuntimeError` branch.
  It catches `ExceptionGroup` and `subprocess.SubprocessError` and returns an `error`
  trial with the formatted diagnostic. It never applies the `"GPU" in str(error)`
  text rule to groups or subprocess failures. The branch catches only
  `ExceptionGroup`, so a `BaseExceptionGroup` that carries `KeyboardInterrupt` still
  propagates cancellation.
- `_query` catches `CalledProcessError` and `TimeoutExpired`, attaches non-empty
  stdout and stderr with `add_note` (decoding bytes defensively), and re-raises the
  same exception. `str(error)` is unchanged, so no classification can change through
  note text.
- Existing `RuntimeError` mapping (`contaminated` when the text contains "GPU",
  otherwise `error`) and `FileNotFoundError` mapping stay byte-identical. Both
  `contaminated` and `error` end the search as `failed`, so search outcomes do not
  change; only the trial is now retained.

Tests to add (fail before the fix):

- the formatter lists the leaves and notes of nested groups and keeps the
  single-exception format;
- the case diagnostic from `estimate_batches` contains every group leaf;
- the probe records grouped and lone subprocess failures as an `error` trial, even
  when leaf or note text contains "GPU", and a `KeyboardInterrupt` group propagates;
- the `RuntimeError` mapping is pinned (with and without "GPU");
- a failing fake nvidia-smi exposes its stdout in notes, keeps the exception type,
  and reaches the persisted trial diagnostic.

Rejected alternative: wrapping failures in a `RuntimeError`. Text containing "GPU"
would reclassify them as `contaminated`.

## Architecture

See [architecture.json](architecture.json). The formatter is pure core code reused by
application and adapter layers. Process effects remain in runtime adapters. There are
no new modules or import edges beyond existing inward ones (`adapters` and
`application` → `core`). Existing `.importlinter` contracts and
`tests/test_architecture.py` negative cases are authoritative.

## Documentation

Update `docs/batch-estimation.md` to state that failed telemetry and cleanup are
retained as `error` trials, with leaf and nvidia-smi output diagnostics. Inspect the
portable corp-skills usage source. This internal evidence change alters no CLI,
configuration or recovery procedure.

## Out of scope

`adapters/runtime/worker_pool.py:151` uses the same leaf-dropping join for
independent case failures. Record it as a follow-up. The selected-L measurement itself
remains blocked on the environmental decision in the source assessment.
