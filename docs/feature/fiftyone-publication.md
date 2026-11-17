# FiftyOne publication

FiftyOne publication is optional visualization: after `cy`, `cy-predict` or `cy-metrics`
produce their results, CY publishes the effective ground truth, the raw predictions and
the exact evaluation outcome of each split into a persistent FiftyOne dataset, so images,
true and false positives, misses and confusion cells can be browsed in the FiftyOne App.
Publication runs in a separate, time-bounded worker process. It is enabled by default, it
can be turned off with `fiftyone.enabled=false`, and its failures only produce warnings:
they never fail an otherwise successful computation or its ClearML task.

## Behavior

### When it runs

- `cy` publishes once after comparison and reporting, when prediction output from this
  run is available; nested prediction and metrics stages do not publish separately.
  `cy-predict` publishes ground truth and predictions; `cy-metrics` publishes ground
  truth, predictions and the evaluated splits. `cy-val` and other commands do not
  publish and do not expose the `fiftyone` group.
- Before work starts the command runs a preflight in a worker (import FiftyOne, list
  datasets). If the preflight fails, a warning is logged and the command continues with
  publication disabled.
- Publication requires the invocation-owned ClearML task; distributed training workers
  never publish.

### What is published

- One persistent dataset per effective ground truth, named
  `<dataset_prefix>-v1-<ground-truth SHA-256>`. It holds one sample per image with its
  split and labelled ground truth. A later run with the same ground truth and media
  paths reuses the completed dataset; a different media identity for the same name
  fails (use the original media paths or another `fiftyone.dataset_prefix`).
- Each task writes its own run, keyed `run_<sha256(task id)>`, with task-specific fields:
  raw `predictions` separate from evaluated fields (`matched_ground_truth`,
  `matched_predictions`, `evaluated_predictions`, `predicted`, `evaluated`, `tp`, `fp`,
  `fn`), each suffixed with the run key. Republishing the same task replaces only its own
  run and evaluations; other tasks' runs are preserved.
- Each evaluated split gets one native FiftyOne detection evaluation (method
  `digital_metrics`) built from the exact matches CY already computed; nothing is
  rematched. Evaluated predictions exclude `filtered` boxes, while the audit overlay keeps
  them without an evaluated status. The persisted evaluation supports loading, reports,
  confusion matrices, patches, rename and delete.
- Evaluation reports keep the original confusion counts, PR curve at IoU 0.50 and AP50,
  AP75 and AP50–95. `mAP` is the mean of the available class AP50–95 values; mAR is not
  available. A restricted subset shows fixed-threshold counts without AP or PR; leaving
  the subset restores the full report. Runs without a stored report show it as
  unavailable.
- Finite, ordered zero-area predictions produced by clipping stay as raw evidence.
  Reversed or non-finite boxes and confidence outside `[0, 1]` are rejected; labelled
  ground truth needs positive geometry. The effective ground-truth identity hashes the
  bytes actually parsed.

### Receipts

- A successful publication writes `fiftyone_publication.json` to the command's output
  directory (the run directory for `cy`). It records the dataset name, task ID, run key,
  ground-truth hashes, whether the dataset was reused, sample count, field mapping,
  split-to-evaluation `evaluation_keys` (empty for prediction-only publication), payload
  paths, completion markers and an aware UTC publication time.
- The same dataset name, run key, reuse flag, sample count, fields and evaluation keys
  are recorded in the `fiftyone_result` section of the canonical `run` configuration.
  No receipt artifact is uploaded to ClearML, and controller cache identity ignores
  these fields.

### Bounded workers

- Every preflight and publication runs in a fresh Python process with no GPU visibility,
  no queue lease and no ClearML task ownership.
- The supervisor drains the worker's output continuously, keeping only a short redacted
  tail for diagnostics, and accepts success only when the worker exits with code `0`
  before its deadline and returns a receipt whose operation, operation ID and task ID
  match and whose dataset and run are marked complete.
- The deadline covers import, the operation and worker exit; after a successful exit,
  cleanup must also finish before it or the operation fails at phase `shutdown`. After a
  timeout or failure, cleanup is bounded separately: up to 5 seconds after a graceful
  stop and 5 more after a forced kill. A
  timeout message names the phase the worker reached (for example `import`, `lock`,
  `write`). If owned processes cannot be proven gone, the scratch directory is retained
  with an unsafe-cleanup marker and the failure says so.
- Partial database state is kept so the same task can retry. Publication never installs
  the App extension.

### Open a published dataset

Run the App with the same database and SDK configuration that publication used. Provide
MongoDB through FiftyOne's bundled service or `FIFTYONE_DATABASE_URI`; publishers that
share a database on one machine also share `FIFTYONE_DATABASE_DIR`, which holds the
publication locks. Keep the referenced media paths readable. Load the dataset named in
the run's receipt, replacing the example path:

```python
import json

import fiftyone as fo

with open("runs/my-run/fiftyone_publication.json", encoding="utf-8") as stream:
    receipt = json.load(stream)
dataset = fo.load_dataset(receipt["dataset_name"])
session = fo.launch_app(dataset)
session.wait()
```

For the native evaluation panels, install the project package in the Python environment
that runs the FiftyOne server, install its App extension explicitly and restart the App:

```bash
uv run --frozen --no-sync python <<'PYTHON'
from clearml_yolo.adapters.fiftyone.panel import install_evaluation_plugin

print(install_evaluation_plugin())
PYTHON
```

The `@clearml-yolo/evaluation` extension adds `native_evaluation` (exact TP/FP/FN,
wrong-class cells and labels) and `evaluation_reports` (full-split PR and AP reports).
Runs published before an evaluation existed gain native evaluations only by publishing
again.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `fiftyone.enabled` | `true` | `false` selects a no-op publisher with no file or database access |
| `fiftyone.preflight_timeout_seconds` | `60` | Preflight deadline, including import and worker exit |
| `fiftyone.publish_timeout_seconds` | `900` | Publication deadline, including import and worker exit |
| `fiftyone.lock_timeout_seconds` | `30` | Wait for the per-dataset publication lock |
| `fiftyone.dataset_prefix` | `clearml-yolo` | Dataset name prefix: letters, digits, `-`, `_`; starts with a letter or digit |

Timeouts must be finite and strictly positive. The group exists for `cy`, `cy-predict`
and `cy-metrics`, for example:

```bash
cy fiftyone.preflight_timeout_seconds=30 fiftyone.publish_timeout_seconds=300
```

FiftyOne's own settings (database, plugin directory) are discovered through its normal
environment and configuration files; CY does not substitute project defaults.

## Failure behavior

- Factory, preflight, request preparation, publication, receipt writing and run-link
  recording failures log a redacted warning and the command continues; the scientific
  outcome and the ClearML task status are unchanged.
- A worker that times out, exits nonzero, returns no receipt or a mismatched or
  incomplete receipt counts as a failed publication, even if it wrote a receipt file.
- Invalid optional FiftyOne SDK configuration takes the same warning path and does not
  block help.
- Cancellation (Ctrl+C, SIGTERM) is not swallowed: it propagates after the worker is
  stopped and reaped.

## Limits

- Worker process ownership needs Linux `/proc` or a Windows job object; on other
  platforms preflight fails and publication is disabled with a warning.
- Publication does not migrate existing datasets or runs.
- Fault-injection tests establish bounded failure behavior only. Live publication
  against a FiftyOne database is established only by the live suite.

## Code and tests

- [`application/use_cases/publication.py`](../../src/clearml_yolo/application/use_cases/publication.py) — warning boundary and receipt recording
- [`adapters/fiftyone/bounded.py`](../../src/clearml_yolo/adapters/fiftyone/bounded.py) — supervised worker and receipt validation
- [`adapters/fiftyone/worker.py`](../../src/clearml_yolo/adapters/fiftyone/worker.py) — worker process
- [`adapters/fiftyone/publisher.py`](../../src/clearml_yolo/adapters/fiftyone/publisher.py) — datasets, runs and overlays
- [`adapters/fiftyone/evaluation.py`](../../src/clearml_yolo/adapters/fiftyone/evaluation.py) — native evaluation import
- [`adapters/fiftyone/panel.py`](../../src/clearml_yolo/adapters/fiftyone/panel.py) — App extension
- [`core/publication.py`](../../src/clearml_yolo/core/publication.py) — options, request and receipt
- Tests: [`test_bounded_fiftyone.py`](../../tests/test_bounded_fiftyone.py),
  [`test_publishing.py`](../../tests/test_publishing.py),
  [`test_publication_commands.py`](../../tests/test_publication_commands.py),
  [`test_publication_data.py`](../../tests/test_publication_data.py),
  [`test_fiftyone_evaluation_results.py`](../../tests/test_fiftyone_evaluation_results.py),
  [`test_fiftyone_panel.py`](../../tests/test_fiftyone_panel.py),
  [`test_fiftyone_compatibility.py`](../../tests/test_fiftyone_compatibility.py)
