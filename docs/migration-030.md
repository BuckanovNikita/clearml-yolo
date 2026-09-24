# Migrating to 0.3.0

Version 0.3.0 removes the project's custom execution automation. YOLO now owns
device selection, batching, AMP, compilation and augmentation through its native
arguments. ClearML tracking is required for every invocation.

## Commands

The installed commands are `cy`, `cy-train`, `cy-predict`, `cy-val`,
`cy-metrics`, `cy-report`, `cy-compare`, and `cy-ground-truth`.

`cy-queue` and `cy-init-config` have been removed. Do not retain generated
configuration trees; pass native YAML with `cfg=<path>` or set wrapper and native
arguments directly.

`cy-val` predicts a checkpoint on validation and requested splits, calibrates the
candidate thresholds on validation, and evaluates the requested data with those
frozen thresholds.

## Native settings

Native values are sparse mappings under `ultralytics`; in the pipeline they are
under `train.ultralytics` and `predict.ultralytics`. A native YAML supplied by
`cfg` is used unchanged. The effective precedence is:

1. Ultralytics defaults.
2. `cfg` YAML.
3. Embedded `ultralytics` mapping, including a value equal to an upstream default.
4. Hydra command-line overrides.

Use an ordinary override for a key already present in the mapping and `+` to add
an absent key:

```bash
uv run cy-train cfg=training.yaml +ultralytics.device=0 +ultralytics.epochs=10
uv run cy ground_truth=ground_truth.csv +train.ultralytics.data=data.yaml \
  +train.ultralytics.device=0 +predict.ultralytics.device=0
```

There is no `auto_gpu`, `--force-gpu`, custom augmentation JSON, or
`clearml.enabled=false` mode. These removed options fail explicitly. Pass native
Ultralytics options such as `device`, `batch`, `amp`, and `compile` directly.
Albumentations remains installed for Ultralytics' native augmentation block; only
the wrapper's JSON augmentation handling is removed.

## Output routing

For `cy`, `run_dir` owns the output layout for the whole pipeline. Do not set
stage-specific output paths or native `project`/`name` values that conflict with
the pipeline training directory; the command rejects conflicting routes. A
standalone output-producing command creates a fresh directory unless you provide
its explicit output path. Input paths are mandatory: stale working-directory files
are never selected implicitly. A configuration cloned in ClearML supplies its
effective native/dataset file to execution; local files are executed unchanged and
only the copies stored in ClearML are sanitized.

```bash
uv run cy run_dir=./runs/experiment-030 \
  ground_truth=ground_truth.csv \
  +train.ultralytics.data=data.yaml \
  +train.ultralytics.device=0 \
  +predict.ultralytics.device=0
```

## Evaluation and comparison

Candidate thresholds are calibrated on `val` once and then frozen for `test`.
When a baseline is available, both baseline and candidate infer the same current
test images with matching inference settings. `cy-compare` receives
`baseline_model`, `candidate_model`, current `ground_truth`, inference settings,
`split=test`, and its output directory.
The pipeline shares all `metrics.evaluation` options with comparison. Standalone
comparison accepts sparse overrides such as `+evaluation.ap_method=continuous`
and `+evaluation.preprocess_preds_conf_threshold=0.5`; omitted IoU and matching
options retain the standalone `iou_threshold` and `matching_strategy` values.

The automatic baseline is the latest completed prod-tagged task other than the
current task. An absent automatic baseline records a skipped comparison. An
explicit task or checkpoint that cannot supply the required model or exact
thresholds fails. Historical dashboards are not comparison inputs. Reports use
the paired current-test dashboards in `comparison_dir`, so developer, business,
and statistical counts describe the same evaluation.

## Tracking and artifacts

Every invocation owns one ClearML task. Nested pipeline stages reuse that owner;
native callbacks and workers do not create tasks or upload artifacts. A task is
completed only after required artifacts have uploaded. Computation, upload, flush,
or interruption failures fail both task and command while retaining local outputs.

Captured material includes sanitized source and resolved configuration, effective
native arguments and output paths, model references, dataset configuration when
provided, evaluation methodology, and the final artifact manifest. Credentials
and source images are never captured. Native console output stays local to prevent
raw argument/URL credentials entering the remote log; sanitized configuration,
metrics, tables and artifact records are published explicitly.
Remote failure status records the exception type; full exception text stays in
local diagnostics because it can contain credentials outside structured fields.

## Local environment tooling

Repository-local agent scripts and automatic environment probes are no longer part
of the application. Local operators can use the global `clearml-yolo-environment`
skill; other environments supply their own ClearML setup and resource management.
Set `clearml.project_name` and `clearml.tags` explicitly. Harness-specific environment
variables no longer rewrite application configuration.

The obsolete generated `conf/` snapshots were removed because they referenced
retired modules. Create native YAML or a small Hydra overlay as shown in the README.
