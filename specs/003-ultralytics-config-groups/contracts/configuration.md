# CLI configuration contract

Five model commands (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`) expose top-level
`ultralytics` and `ultralytics_predict`. Native group files contain native keys at their root.
Generated examples select `ultralytics/default.yaml` and `ultralytics_predict/default.yaml`
through Hydra defaults. Other command-specific wrapper options retain their existing meaning.

The shared file covers installed native defaults, with original comments and order; irrelevant
training settings are commented. Pasting the complete unchanged upstream file is supported.
The prediction file activates `conf: 0.001` and documents the remaining options as comments.
Composed prediction keys inherit applicable shared values, so ordinary overrides work:

```bash
cy --config-dir configs --config-name cy \
  ultralytics.epochs=10 ultralytics.imgsz=1280 ultralytics_predict.batch=8
```

Prediction explicit values win over shared values including shared CLI overrides. Explicit
nulls and values equal to native defaults are not treated as absent. Prediction-specific CLI
overrides win over prediction file values. Native execution receives stage-applicable settings.

`train.ultralytics`, `predict.ultralytics`, wrapper `cfg`, non-null native `cfg` and comparison
`inference` native settings are removed and fail with migration guidance. Comparison-only
controls such as cache reuse remain. Upstream `cfg` comments remain documentation only.

Pipeline `run_dir`, produced checkpoint and selected images own execution routing and inputs.
A shared training model is replaced for prediction by the produced checkpoint; conflicting
explicit prediction model selections fail. Comparison uses identical native inference settings
for both roles. `cy-val` remains prediction plus existing calibration/evaluation.

`cy-init-config DIRECTORY [--force]` protects all ten generated files and their parent paths
before writes; force replaces regular generated files only, never symlinks or directories.
Initialization creates no task and imports no model runtime.

Stage-owned exceptions: prediction `model: null` means no checkpoint override; `mode`
defaults to `predict`, and `project`/`name` default to null for stage output routing. These
fields do not inherit training routing. Comparison rejects non-null prediction model/project/name
overrides; use its model references and output directory. `cy-train` accepts both groups for
consistent composition but only uses shared training settings. Native compatibility aliases and
custom `augmentations`, absent from the upstream template, are retained when explicitly supplied.
