# Pipeline prerequisites and observations

## Inputs and configuration

`cy` uses the packaged pipeline configuration unless a tree created with
`cy-init-config` is selected with `--config-dir` and `--config-name`. Regenerate
that tree when its composition schema no longer matches the package.

The enabled prediction, metrics, and comparison stages require the configured
ground-truth CSV to exist. `clearml.enabled=false` requires `skip_compare=true`
unless the comparison baseline is named explicitly, because the normal baseline
lookup uses ClearML. `report/baseline=none` is the packaged-config group override;
an exported configuration tree expresses the same choice as
`report.baseline.source=none`.

`run_dir` re-enters or redirects the selected run. Do not attempt to route a
pipeline with stage-specific output overrides; the pipeline supplies those paths
to its stages.

## GPU and queue

`auto_gpu.min_gpus` is the minimum allocation and `auto_gpu.max_gpus` is an
optional cap. `auto_gpu.batch_size` is per GPU. If no explicit batch is given,
the project reuses a successful observed value for the stage and hardware or its
packaged fallback; do not infer a usable batch from VRAM arithmetic.

With `auto_gpu.queue.enabled=true`, the filesystem queue coordinates waiting
runs and there is no no-queue timeout. With it disabled,
`auto_gpu.wait_timeout_seconds` applies. The queue directory is configurable by
`auto_gpu.queue.dir` or `CLEARML_YOLO_QUEUE_DIR`; its default is a host-specific
directory under `/tmp/clearml-yolo`. `cy-queue` is interactive and requires a
terminal.

## What a real run demonstrates

An offline run demonstrates train-to-output wiring but not ClearML uploads. A
ClearML-backed run needs authenticated credentials and should appear as a
completed task with its output model and metric artifacts. Model labels come
from the checkpoint, not ClearML metadata.

Comparison needs a completed baseline that the candidate is configured to find.
Run baseline and candidate in a disposable project and keep their output
directories separate. Do not manufacture a comparison by reusing a production
task or by changing shared service state.
