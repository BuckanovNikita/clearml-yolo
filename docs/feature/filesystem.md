# Filesystem

CY keeps everything it writes inside one workspace directory, `CY_HOME`: run outputs,
Hydra logs, the prepared-dataset cache, batch-size tables, model preparation receipts and
per-invocation scratch. Inputs such as CSVs, images and checkpoints may live anywhere,
and the libraries CY uses (ClearML, Ultralytics, FiftyOne, Torch, Hugging Face and
others) keep their own configuration and cache locations. Every experiment command,
`cy-init-config`, `cy-download-weights` and measuring `cy-batch-estimate` set up the
workspace at startup; destinations outside it are rejected before anything is created.

## Behavior

### Workspace

`CY_HOME` defaults to the launch directory. A relative value resolves against the launch
directory, and the absolute result is fixed for the whole invocation before Hydra
composes anything; the directory is created when missing. Explicit relative input and
output paths keep their ordinary working-directory meaning (Hydra does not change the
working directory). Importing the package creates nothing. `cy-dedup` and
`cy-batch-estimate --list` do not initialize the workspace.

### Project-owned locations

| Content | Default beneath `CY_HOME` | Owner |
| --- | --- | --- |
| Task runs and the `latest` link | `runs/` | [commands-and-configuration](commands-and-configuration.md) |
| Hydra logs and sweeps | `outputs/`, `multirun/` | Hydra |
| Prepared CSV datasets | `.cache/clearml-yolo/datasets/` | [datasets-and-ground-truth](datasets-and-ground-truth.md) |
| Editable training batch sizes | `.config/clearml-yolo/batch-sizes.yaml` | [batch-estimation](batch-estimation.md) |
| Batch measurement evidence | `.config/clearml-yolo/batch-estimates.json` | [batch-estimation](batch-estimation.md) |
| Managed model assets, sources, receipts | `.cache/clearml-yolo/{models,sources,preparation}/` | [model-assets](model-assets.md) |
| Invocation scratch and console logs | `.tmp/cy-runtime-*` | this feature |
| Queued-job logs and progress | `.cy/queue-logs/`, `.cy/queue-status/` | [queue](queue.md) |

Every application-owned output, cache entry, log, configuration snapshot and temporary
destination must resolve beneath `CY_HOME`, following symlinks, including the final
target of a symlink that already exists. This applies to `run_dir`, `output_dir`,
`output`, `dataset_cache_dir`, native `project`/`name`/`save_dir`, Hydra run and sweep
directories, Hydra log handlers and configuration snapshots (checked for every sweep
member and the sweep manifest before the first job), native trainer and predictor output
trees, and generated files such as comparison archives. Symlinks that stay inside the
workspace remain valid destinations. Existing data is neither migrated nor deleted.

### Invocation scratch

Each top-level invocation creates a unique arena `cy-runtime-*` under
`CY_RUNTIME_TEMP_ROOT` (default `CY_HOME/.tmp`; a relative value resolves against
`CY_HOME`). Console capture logs are written to its `logs/` directory. Resolved execution
copies of configuration files, DDP relay files, publication protocol files and similar
project temporaries are created inside the arena. Nested calls in the same process reuse
it; a spawned runtime scope creates its own, and child processes may keep using the
parent's arena. A programmatic caller of `native_runtime()` gets its own retained arena;
outside any arena, project temporaries go directly under `CY_RUNTIME_TEMP_ROOT`. Arenas
are kept after success, failure, interruption and cancellation. Startup performs no
scan, recovery or recursive deletion of earlier arenas. `TMPDIR`, `TMP`, `TEMP` and
`tempfile.tempdir` are not changed, so library temporary files follow the library's own
policy.

Atomic writes (text outcomes, comparison results, dataset cache entries) go through a
temporary sibling of the destination that the writer removes on success and failure. A
failed dataset preparation removes only its own staging directory.

### Library configuration and caches

CY does not change `HOME`, XDG variables, or the configuration, cache and credential
selectors of ClearML (including legacy Trains selectors), FiftyOne and ETA, Ultralytics,
Matplotlib and fontconfig, Torch, Triton, CUDA, Numba, Hugging Face, RF-DETR and
Roboflow, Keras, Python bytecode, Requests and netrc, or AWS. Selectors outside `CY_HOME`
are valid; CY neither validates nor normalizes them, creates no placeholder
configuration files and substitutes no SDK constants. SDKs may cache settings at import,
so changing `CY_HOME` later does not move them. The exceptions are explicit model
preparation, which writes model assets into native library caches, and both preparation
and YOLO batch estimation, which persist an absolute Ultralytics `weights_dir`
([model-assets](model-assets.md), [batch-estimation](batch-estimation.md)). Native ClearML
callback switches are changed in memory only and restored on exit; apart from the
`weights_dir` persisted by `cy-download-weights`, the automatic preparation pass before
`cy` and YOLO batch estimation, the Ultralytics settings file is not rewritten.

Libraries that read configuration from the working directory keep doing so. To use
SDK settings or caches that sit inside the workspace, select them explicitly through the
library's own variables before the command starts, for example `CLEARML_CONFIG_FILE`,
`CLEARML_CACHE_DIR`, `YOLO_CONFIG_DIR`, `FIFTYONE_CONFIG_PATH` or `TORCH_HOME`.

## Configuration

| Variable or setting | Default | Effect |
| --- | --- | --- |
| `CY_HOME` | launch directory | Workspace for every project-owned write |
| `CY_RUNTIME_TEMP_ROOT` | `CY_HOME/.tmp` | Parent of invocation arenas; must be inside `CY_HOME` |
| `dataset_cache_dir` | `null` | Prepared-dataset cache; `null` uses the default above |

## Failure behavior

- A project destination outside the workspace fails before it is created: `Project write
  destination <path> must be contained beneath CY_HOME=<root>; choose a destination
  inside CY_HOME or select the intended project workspace. External input and library
  configuration paths remain supported.`
- An external `CY_RUNTIME_TEMP_ROOT` fails before the workspace is created.
- Native trainers and predictors fail before writing when an existing entry in their
  output tree leads outside the workspace.
- Invalid or incomplete dataset cache entries fail and are left in place for inspection.
- Failing to update `runs/latest` only logs a warning.

## Limits

- Containment checks assume cooperating callers: a filesystem entry replaced
  concurrently after validation is not detected.
- Nothing is cleaned automatically. Remove retained arenas, cache entries or old runs only
  as deliberate maintenance after confirming that the relevant workspace and all its
  descendant processes are idle; age, host or PID alone does not establish that.
- Durable outputs, datasets, library caches and partial publication state persist until
  removed by the user.
- Queue metadata and coordination roots are configured by the separate `cy-queue` package
  and never derive from `CY_HOME`; CY execution, including ClearML Agent replay, creates
  no queue storage.

## Code and tests

- [adapters/runtime/bootstrap.py](../../src/clearml_yolo/adapters/runtime/bootstrap.py) —
  workspace freeze, containment check, retained arenas
- [adapters/storage/filesystem.py](../../src/clearml_yolo/adapters/storage/filesystem.py) —
  `write_path`, output-tree preflight, `temporary_root`
- [adapters/storage/file_io.py](../../src/clearml_yolo/adapters/storage/file_io.py) —
  atomic text writes
- [entrypoints/hydra/validation.py](../../src/clearml_yolo/entrypoints/hydra/validation.py)
  — Hydra and project destination preflight
- Tests: [test_filesystem.py](../../tests/test_filesystem.py),
  [test_runtime_bootstrap.py](../../tests/test_runtime_bootstrap.py),
  [test_project_output_containment.py](../../tests/test_project_output_containment.py),
  [test_native_output_containment.py](../../tests/test_native_output_containment.py),
  [test_hydra_sweep_configuration.py](../../tests/test_hydra_sweep_configuration.py)
