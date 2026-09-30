# Migrating from 0.3.0 to current configuration

This guide describes the current checkout. The [0.3.0 release notes](releases/0.3.0.md)
record that release's interface; subsequent changes removed its raw `cfg`
loading and sparse nested native mappings. Use the [current contract index](current-contracts.md)
for maintained requirements by topic.

## Commands and editable examples

The commands are `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, `cy-ground-truth`, and `cy-init-config`. `cy-queue` remains removed.
`cy-init-config DIRECTORY [--force]` writes eight command examples and the native groups
without a ClearML task or model runtime. Existing examples are protected; force replaces
only the supported regular files and preserves unrelated content.

```bash
uv run cy-init-config ./conf
uv run cy-train --config-dir=./conf --config-name=cy-train \
  ultralytics.data=data.yaml ultralytics.epochs=10
```

Fill required `???` inputs and configure ClearML before execution. Merge desired wrapper
values into freshly generated examples rather than executing old trees unchanged.

## Native settings and output routing

All model commands use top-level `ultralytics` and `ultralytics_predict`. Paste native
YAML at the root of the appropriate group file, without wrapper indentation. Shared
prediction values use visible references; explicit literals, including supported nulls
and default-equivalent values, retain their precedence. Prediction reads only its resolved
group. Ordinary overrides change known native keys without `+`.

Raw wrapper `cfg`, non-null native `cfg`, nested `train.ultralytics` / `predict.ultralytics`
and native fields under comparison `inference` are removed. See the
[native-group migration](migration-ultralytics-groups.md) for replacements and defaults.
Device, batch, AMP, compilation and native augmentation belong to Ultralytics. GPU
scheduling, leases, queues, batch tuning, wrapper augmentation JSON, `--force-gpu` and
`clearml.enabled=false` remain removed.

`run_dir` owns pipeline output routing. Conflicting stage paths and native training
`project`/`name` fail. Standalone output-producing commands use fresh output directories
and explicit inputs. Training and prediction devices are independent:

```bash
uv run cy run_dir=./runs/experiment \
  ground_truth=ground_truth.csv \
  ultralytics.device=0 ultralytics_predict.device=0
```

The pipeline can derive its training dataset from the CSV. Standalone `cy-train` without
`ground_truth` uses explicit native `ultralytics.data`.

## Evaluation and comparison

Candidate thresholds are calibrated on `val` once and frozen for requested evaluation
splits. Pipeline comparison uses current test images. Standalone `cy-compare` defaults to
`split=test` and accepts another ground-truth split. Both models infer the
same selected images with matching settings and use exact frozen thresholds; comparison
does not recalibrate. `cy-val` performs prediction, calibration and evaluation independently.

The pipeline forwards `metrics.evaluation` to comparison. Standalone comparison accepts
sparse evaluation overrides such as `+evaluation.ap_method=continuous`; omitted IoU and
matching options retain `iou_threshold` and `matching_strategy`.

The automatic baseline is the latest completed prod-tagged task excluding the current
task. Missing automatic baseline skips comparison; invalid explicit references or missing
exact thresholds fail. Historical dashboards are not comparison inputs. Reports consume
the paired results and manifest split from `comparison_dir`. Source-task links provide
provenance; retrieved weights/thresholds do not replace current comparison settings.

## Tracking and replay

Each execution invocation owns one ClearML task. Nested stages reuse it; workers do not
create tasks or publish. Installed native owner callbacks publish Scalars, Plots, permitted
training/validation previews and one best Output Model. Completion requires verified
required publications and a successful SDK flush. Computation, callback, upload, flush
and interruption errors fail task and command while retaining local output.

Performance CSVs, consolidated evaluation/comparison workbooks and final reports are
artifacts. Effective/requested native YAML, image manifests, NDJSON, archives and diagnostic
or publication receipts remain local. There is no configuration artifact or duplicate
checkpoint artifact. Canonical `run`, consumed dataset and explicit report Configuration
Objects, plus native `General`, provide remote replay. See the
[publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md).

Active interpolations in consumed YAML/JSON resolve before execution and publication;
source bytes remain intact. Executable copies and sanitized remote copies are separate.
Credentials never enter published configuration; native console output and full failure
details remain local. See the [resolution contract](../specs/009-resolved-config-uploads/contracts/configuration-files.md).

## Environment guidance

Use the applicable global environment skill for endpoints, credentials, capacity and
task-owned cleanup. Pass `clearml.project_name` and `clearml.tags` explicitly; application
configuration does not derive them from an agent harness. Historical environment commands
are evidence, not current run recipes.
