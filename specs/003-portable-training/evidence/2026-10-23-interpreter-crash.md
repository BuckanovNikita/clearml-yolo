# Interpreter crash investigation — 2026-10-23

A full CY pytest process terminated with `SIGILL` during
`tests/test_model_assets.py::test_concurrent_download_and_offline_placement`.
The cause remains unconfirmed. Fifteen bounded subprocess investigations passed;
none reproduces or explains the original crash. No production code, test
suppression, dependency change or runtime workaround was applied for this incident.

## Original observation

The full-suite log `.tmp/portable-clean-pytest.log` reports the fatal signal after
approximately 72% of the suite. Faulthandler identifies the current Requests worker
as **garbage-collecting** while constructing a `CaseInsensitiveDict` during
`urllib3.connectionpool.urlopen`. The other three asset consumers are waiting in
filelock's polling sleep; the main thread awaits executor results and the local
HTTP server awaits connections. The log contains no preceding Python exception,
asset assertion failure or lock-corruption report.

The kernel log confirms signal 4 at 17:33:29 host-local time. Its recorded instruction
address is immediately after a `tgkill` syscall, consistent with fatal-signal
re-raising; this does not identify the original native instruction or library.
No core dump or native stack was captured from the original process.

An earlier full run completed with 3,041 passing tests and four architecture-test
failures, recorded in `.tmp/portable-final-pytest.log`. Those architecture failures
were separately identified and corrected by the parent. That earlier run included
the same concurrent asset test without an interpreter crash.

The parent started a separate hook suite while the crashing full suite was still
running. The hook invocation exported `UV_NO_SYNC=1`, inherited by its children,
and the outer command used `uv run --frozen --no-sync`. The parent confirmed that
no synchronization of the shared environment occurred. Separate candidate-install
and dependency-floor checks used isolated environments. Overlapping workload is an
observed condition, not an established cause.

## Bounded reproduction results

All attempts used the existing Python 3.12.13 environment and enabled faulthandler.
Each attempt ran in a fresh subprocess, with a per-process deadline. No second
broad full-suite run was launched by this investigation.

| Experiment | Attempts | Result |
| --- | ---: | --- |
| Exact concurrent-download test alone | 10 | All passed; one test per process |
| Faster R-CNN backend suite, then the target | 1 | 21 passed |
| Detector export suite, then the target | 1 | 52 passed |
| DEIM backend suite, then the target | 1 | 28 passed |
| All three native suites, then explicit worker-thread generation-2 collection and the target | 2 | 99 passed in each process; each forced collection reclaimed 131 objects |

The exact-test command was:

```bash
.venv/bin/python -X faulthandler -m pytest \
  tests/test_model_assets.py::test_concurrent_download_and_offline_placement -q
```

Native-preceded attempts added the relevant `tests/test_fasterrcnn_backend.py`,
`tests/test_detector_export.py` or `tests/test_deim_backend.py` before that node.
The final two attempts used a scratch-only pytest plugin to invoke `gc.collect()`
on a worker thread immediately before the target, with a bounded join. That plugin
was not added to production tests or configuration. Process exit codes, timings,
logs and diagnostic plugin are retained in `.tmp/asset-sigill-investigation/`.

## Interpretation and remaining limits

The trace establishes the Python collection location, not the native origin of the
signal. It does not demonstrate a Requests, filelock or asset-resolver defect.
The lock waiters exhibit expected coordination in the captured trace.

Larger-suite state, delayed native-object cleanup and scheduling differences remain
hypotheses. The native-preceded and forced-GC experiments do not support a simple,
deterministic failure from those preceding detector suites alone. They do not
prove that all possible native cleanup sequences are safe.

There is no evidence-backed production fix from this investigation. Keep the
concurrent test enabled. If the full failure recurs, capture a task-scoped native
stack/core with a disk bound, the exact test order and the invocation environment
before selecting a change. A later passing run must be recorded separately and
must not be described as proof that this unexplained crash was fixed.
