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
`conf: 0.001`; other applicable values inherit from the shared group until explicitly
overridden. Explicit prediction values, including null/default values, win over shared CLI
settings. Set a valid prediction batch explicitly when using training AutoBatch.

Non-null native `cfg` is forbidden even when pasted from another configuration. Its original
comment is retained as documentation. Upstream irrelevant settings may remain in a pasted
full file; stage execution filters them and effective YAML comments them out.

The pipeline still owns produced checkpoint, selected images, mode and output routing.
Effective native YAML appears locally and in ClearML configuration objects/artifacts, with
split/role variants and retained prediction source manifests. Native replay uses the external
Ultralytics command's `cfg` option, not a clearml-yolo option.

The authoritative feature contract is [configuration.md](../specs/003-ultralytics-config-groups/contracts/configuration.md).

Prediction checkpoint and output fields are stage-owned: `model: null` selects the pipeline
checkpoint (or standalone weights/shared model), `mode` defaults to `predict`, and null
`project`/`name` select stage output routing. They do not inherit training paths. For comparison,
select checkpoints through model references and output routing through `output_dir`; explicit
prediction model/project/name values fail.
