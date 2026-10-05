# CLI and configuration contract

Nine entrypoints: cy, cy-train, cy-predict, cy-val, cy-metrics, cy-report, cy-compare,
cy-ground-truth and cy-init-config.

`cy-init-config DIRECTORY [--force]` creates missing parent directories and writes one
editable YAML per execution command, named after that command (including `cy-val.yaml`).
Examples compose with `COMMAND --config-dir DIRECTORY --config-name COMMAND` and preserve
current defaults, native groups and required `???` inputs. It also writes
`ultralytics/default.yaml` and `ultralytics_predict/default.yaml`. Comments explain input
paths and native overrides. Initialization is local only: no ClearML task or model execution.
Existing example paths are checked before any writes; without `--force`, collisions fail.
`--force` replaces regular example files, preserves unrelated files and rejects symlink or
directory destinations. Filesystem errors produce a nonzero exit with a CLI error message.

Native settings use top-level `ultralytics` and `ultralytics_predict` groups for every model
command. The shared group covers upstream defaults and original comments; prediction inherits
applicable values and applies explicit overrides, including nulls/default values. Ordinary
Hydra overrides work without `+` for known native keys. Prediction confidence defaults to 0.001.
Prediction device defaults independently to [-1]; training device remains null. Example-only
controlled-key comments and active-first sections are defined in the
[cleanup contract](../../007-detection-config-cleanup/contracts/configuration-and-artifacts.md).
Native group files have native keys at their root. Stage-irrelevant settings are excluded from
execution and commented in effective native YAML. Wrapper controls remain separate.
Raw wrapper `cfg`, non-null native `cfg`, nested stage mappings and duplicate native comparison
inference settings fail ordinary strict validation. See the current
[configuration contract](../../003-ultralytics-config-groups/contracts/configuration.md).
Source configurations and resolved configuration are captured before execution.

`run_dir` routes the whole pipeline. Native project/name that disagree with the chosen
pipeline training directory fail. Standalone training honors explicit native project/name;
otherwise it creates an isolated run rooted at
`$CY_HOME/runs/<safe-project>/<safe-task>-<task-id>/` using the active ClearML identity.
Standalone output-producing commands default to a fresh directory and require explicit input
paths; no silently shared output directories. See the maintained
[filesystem ownership contract](../../../docs/filesystem-policy.md) for automatic and explicit
destination rules.
`cy-val` accepts weights, ground_truth, ultralytics, ultralytics_predict, evaluation, splits and output_dir;
it predicts required val plus requested splits and evaluates at frozen validation thresholds.
`cy`, `cy-val`, and `cy-metrics` default to train/val/test, with explicit subsets preserved.
Standalone `cy-compare` accepts `split=<name>` and defaults to `test`; the pipeline fixes its
comparison to `test`. `cy-report` reads the paired split from `comparison_manifest.json`, so
its output names and content follow the comparison rather than assuming test. `cy-val` never
publishes to FiftyOne.

Comparison takes baseline_model/candidate_model references, current ground_truth, ultralytics, ultralytics_predict,
a standalone split override (default `test`) and statistical options. Automatic baseline is latest completed prod excluding
current task. Explicit local models require weights and exact thresholds; explicit invalid
inputs fail. Explicit threshold maps remain authoritative; task weights and stored thresholds
follow the [recovery contract](../../012-remove-legacy-compatibility/contracts/task-recovery.md),
including historical payload/checkpoint alternatives and dashboard precision warnings.
Reports consume the paired evaluated dashboards named by the local comparison manifest, not
stored historical dashboards. Missing automatic baseline records a skipped comparison.
Developer, business and statistical workbooks retain classes present in only one model.
The supporting model keeps its measured values; unavailable model values and comparisons
render as `NA`, never synthetic zeros. Developer/business training-count eligibility remains
per model. Each model's averages and business verdict inputs use its own eligible classes,
with population sizes disclosed; display placeholders do not enter those aggregates.
Per-class differences require both operands. Statistical tests and pooled comparisons use
the same shared eligible class population; untestable rows do not enter the BH family or
receive a significance verdict. With no comparable classes, reports still show available
metrics and mark pooled comparisons unavailable. Exclusions explain noncomparability rather
than removing an otherwise eligible model's metrics.
Standalone comparison uses the `evaluation` mapping; matching options are configured only as
`evaluation.iou_threshold` and `evaluation.matching_strategy`.
The pipeline forwards the full `metrics.evaluation` configuration to comparison.

Unsupported options must fail rather than be silently ignored. Every execution command
requires ClearML tracking.

`cy` and `cy-train` accept `dataset_cache_dir=null`, which selects
`CY_HOME/.cache/clearml-yolo/datasets` independently of `XDG_CACHE_HOME`, or an explicit shared
directory outside run outputs. CSV SHA-256, format and preparation version identify
entries. NDJSON preserves original filename casing; flat names remain numbered. Images are
immutable and corrections require explicit cache invalidation while not in use.
`cy-train` requires `ground_truth`; `ultralytics.data` is prepared from that CSV and cannot
replace the command input.

## Evaluation input and output safety

Logical split names remain unchanged in manifests, evaluation payloads and result mapping keys.
Every split-derived filename and artifact component uses UTF-8 percent encoding for unsafe
characters, including path separators, percent signs and dots. Common train/val/test names retain
their existing spelling. This keeps outputs beneath their destination and avoids collisions with
literal encoded-looking split names.

Evaluation accepts matching strategies `greedy`, `hungarian`, `iou_prior` and AP methods `interp`,
`continuous`; unsupported values fail. IoU and false-discovery `q` must be finite probabilities
in the inclusive interval `[0, 1]`. Reusable scoring/statistical boundaries apply the same checks.
Baseline lookup requires every ordinary requested tag using the SDK all-tags operator, excludes
the current task and matches the entire task name with grouped regex anchoring.
