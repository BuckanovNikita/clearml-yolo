# Migration to native Ultralytics groups

Regenerate examples into a fresh directory with `cy-init-config DIRECTORY`; merge desired
wrapper values into the new command examples rather than reusing old nested native mappings.

| Removed interface | Replacement |
|---|---|
| `cfg=training.yaml` or `train.cfg=training.yaml` | Paste file contents into `DIRECTORY/ultralytics/default.yaml` |
| `train.ultralytics.epochs=10` | `ultralytics.epochs=10` |
| `predict.ultralytics.batch=8` | `ultralytics_predict.batch=8` |
| Native fields under comparison `inference` | Shared/prediction groups; retain comparison-only controls |
| `+ultralytics.device=0` for a known native key | `ultralytics.device=0` |

Use native keys at the root of each group file. The generated prediction file activates
all applicable parameters. Shared values use visible references; stage-specific values such
as conf and batch are explicit literals. Prediction literals, including supported null/default
values, win over shared CLI settings. Training AutoBatch does not change prediction batch=1.

Non-null native `cfg` is forbidden even when pasted from another configuration. Its original
comment is retained as documentation. Upstream irrelevant settings may remain in a pasted
full file; stage execution filters them and effective YAML comments them out.

The pipeline still owns produced checkpoint, selected images, mode and output routing.
Effective native YAML appears locally and in ClearML configuration objects/artifacts, with
split/role variants and retained prediction source manifests. Native replay uses the external
Ultralytics command's `cfg` option, not a clearml-yolo option.

The current contract is [native configuration](../specs/005-explicit-detection-config/contracts/native-configuration.md).

Prediction checkpoint and output fields are stage-owned: `model: null` selects the pipeline
checkpoint (or standalone weights), `mode` defaults to `predict`, and null
`project`/`name` select stage output routing. They do not inherit training paths. For comparison,
select checkpoints through model references and output routing through `output_dir`; explicit
prediction model/project/name values fail.

## Complete detection configuration

Regenerate old sparse examples into a fresh directory and reapply intended overrides.
Prediction now lists every applicable parameter, using visible shared references or explicit
stage values. It never merges training arguments at execution time. Standalone prediction
requires weights or ultralytics_predict.model; the training architecture is not a fallback.

Project defaults are imgsz=960, compile=true, nms=true, and training model=yolo11n.pt.
Prediction has explicit conf=0.001, batch=1, rect=true, save=false. Null/false remains
meaningful where native supports it; null image size is invalid. Native stride normalization
is retained in normalized-target records alongside requested arguments and replay YAML.
Deprecated half/int8/end2end aliases must be replaced by canonical quantize/nms settings.
Task-specific losses/augmentations, video options and export-only parameters are commented;
embedding output is incompatible with detection records and rejected when non-null.

Python callers must compose complete settings before invoking tasks or helpers. Missing native
keys produce a configuration error rather than helper defaults. Command-owned model, data,
source and output derivations retain the dataset/pipeline contracts.
