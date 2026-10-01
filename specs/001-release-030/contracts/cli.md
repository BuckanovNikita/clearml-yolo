# CLI and configuration contract

Nine entrypoints: cy, cy-train, cy-predict, cy-val, cy-metrics, cy-report, cy-compare,
cy-ground-truth and cy-init-config. cy-queue remains removed.

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
inference settings fail with migration guidance. See the current
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
inputs fail. Tracked models prefer the exact validation-threshold CSV and retain historical
per-split threshold payload compatibility; explicitly supplied thresholds remain exact.
Reports consume the paired evaluated dashboards named by the local comparison manifest, not
stored historical dashboards. Missing automatic baseline records a skipped comparison.
Standalone `evaluation` is a sparse mapping (`+evaluation.ap_method=continuous`);
its supplied values override legacy `iou_threshold` and `matching_strategy`.
The pipeline forwards the full `metrics.evaluation` configuration to comparison.

Removed auto_gpu, force-gpu, augmentation JSON and clearml.enabled options
must fail rather than be silently ignored. No public disabled-tracking mode.

`cy` and `cy-train` accept `dataset_cache_dir=null` (explicit XDG cache or `CY_HOME` default) or an
explicit shared directory outside run outputs. CSV SHA-256, format and preparation version identify
entries. NDJSON preserves original filename casing; flat names remain numbered. Images are
immutable and corrections require explicit cache invalidation while not in use.
