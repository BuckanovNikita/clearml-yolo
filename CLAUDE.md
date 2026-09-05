# clearml-yolo

`clearml-yolo` is a Python 3.12 set of Hydra/hydra-zen applications for YOLO
training, prediction, metrics, reports, and model comparison. `cy` runs the
pipeline; `cy-train`, `cy-predict`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth`, and `cy-init-config` run individual stages. `cy-queue` is
an argparse/Rich queue viewer and does not compose Hydra configuration.

Keep user-facing README text in Russian. Keep code comments and log messages in
English.

## Route work deliberately

- For a real pipeline run, GPU allocation, a queue check, ClearML artifacts, or
  a baseline comparison, load `running-end-to-end-tests`.
- For server reachability, credentials, or the shared ClearML deployment, load
  `running-clearml-server`.
- Read `pyproject.toml` for the current commands, dependency constraints, and
  import-linter contracts. The mocked suite does not establish that a pipeline
  can train, use a GPU, or upload artifacts.

## Project contracts

Import layers are enforced by `lint-imports`:

```
apps -> config_tree -> configs -> tasks -> comparison -> domain modules -> run_queue | run_identity
```

`configs` builds task configuration and remains above `tasks`. Keep ClearML SDK
access in the ClearML adapters and tasks; `run_queue` and `run_identity` remain
filesystem-only bottom-layer modules.

Shared pipeline values (`clearml`, `auto_gpu`, `ground_truth`, `splits`,
`weights`, `run_id`, and `run_dir`) are handed to stages by the pipeline. Set
`run_dir` to redirect a pipeline run; stage output paths are not reliable
pipeline overrides. Use `cy-init-config` to create an editable config tree and
recreate a generated tree when its composition schema becomes stale.

`auto_gpu.force=true` (or `--force-gpu`) bypasses queueing and GPU safety
guards, including lease protection. Do not use it for ordinary verification.
With the normal queue enabled, a run waits in the filesystem queue; with it
disabled, `auto_gpu.wait_timeout_seconds` bounds the wait.

## Proportional verification

For a documentation-only change, validate the changed Markdown and referenced
paths. For code or commit work, choose relevant repository gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

The `tests/test_ultralytics_params.py` test intentionally imports the installed
Ultralytics configuration; other tests may stub ClearML, Ultralytics, or Torch.
Use the end-to-end skill when a change needs evidence beyond those static or
mocked checks.

## ClearML facts

The local ClearML server is a shared machine service, outside this repository.
Its endpoint and ownership contract are in `running-clearml-server`; do not
assume a checkout path or manage its lifecycle from this project.

ClearML model metadata does not enumerate labels; obtain class names from the
checkpoint. Dashboard confidence thresholds are rounded; use the
`metrics_best_confidences_<split>` artifact for exact per-class values.
