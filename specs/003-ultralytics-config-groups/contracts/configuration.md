# CLI configuration contract

Five model commands (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`) expose top-level
`ultralytics` and `ultralytics_predict`. Native group files contain native keys at their root.
Generated examples select `ultralytics/default.yaml` and `ultralytics_predict/default.yaml`
through Hydra defaults. Other command-specific wrapper options retain their existing meaning.

The shared file covers installed native defaults with original comments. Generated examples
place active detection settings first, then commented cy-controlled and stage-inapplicable
settings, retaining upstream order within each section. Pasting the unchanged upstream file
is supported. Prediction lists applicable settings and shared references, with independent
`device: [-1]`, `conf: 0.001`, `batch: 1`, `rect: true`, and `save: false`. Training device
remains null. Ordinary overrides work:

```bash
cy --config-dir configs --config-name cy \
  ultralytics.epochs=10 ultralytics.imgsz=1280 ultralytics_predict.batch=8
```

Prediction explicit values win over shared values including shared CLI overrides. Explicit
nulls and values equal to native defaults are not treated as absent. Prediction-specific CLI
overrides win over prediction file values. Native execution receives stage-applicable settings.

`train.ultralytics`, `predict.ultralytics`, wrapper `cfg`, non-null native `cfg` and comparison
`inference` native settings are unsupported and fail ordinary strict validation. Comparison-only
controls such as cache reuse remain. Upstream `cfg` comments remain documentation only.

Pipeline `run_dir`, produced checkpoint and selected images own execution routing and inputs.
A shared training model is replaced for prediction by the produced checkpoint; conflicting
explicit prediction model selections fail. Comparison uses identical native inference settings
for both roles. `cy-val` remains prediction plus existing calibration/evaluation.

`cy-init-config DIRECTORY [--force]` protects all ten generated files and their parent paths
before writes; force replaces regular generated files only, never symlinks or directories.
Initialization creates no task and imports no model runtime. Example-only commenting leaves
Hydra composition and runtime records complete; see the
[example/routing contract](../../007-detection-config-cleanup/contracts/configuration-and-artifacts.md).

Stage-owned exceptions: prediction `model: null` means no checkpoint override; `mode`
defaults to `predict`, and `project`/`name` default to null for stage output routing. These
fields do not inherit training routing. Comparison rejects non-null prediction model/project/name
overrides; use its model references and output directory. `cy-train` accepts both groups for
consistent composition but only uses shared training settings. Unknown native keys
fail strict validation; custom `augmentations`, absent from the upstream template, remain
available when explicitly supplied.
