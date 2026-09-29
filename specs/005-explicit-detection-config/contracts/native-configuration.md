# Native Configuration Contract

## Public groups

ultralytics owns detection training and its internal validation. ultralytics_predict owns
all application prediction, including cy-val and cy-compare. Ordinary CLI overrides remain.
Generated prediction YAML lists all applicable keys, with cy-controlled keys commented
only in examples; see the [cleanup contract](../../007-detection-config-cleanup/contracts/configuration-and-artifacts.md). Shared references are visible; changing
a reference to a literal makes it independent. A prediction literal always wins.

Project defaults: training model yolo11n.pt, imgsz 960, compile true, nms true. Prediction
references shared imgsz/compile/nms and uses device [-1], conf 0.001, batch 1, rect true,
save false. Training device remains null; prediction device is independent.
Training's native conf null is preserved. Model/project/name are prediction-local null;
model is provided by weights or explicit ultralytics_predict.model. No training-model fallback.

## Validation and filtering

Known detection-irrelevant settings remain commented and are omitted from execution.
Unknown keys and non-null cfg fail with guidance. Non-detect task, wrong stage mode,
non-null embed and invalid image size fail rather than silently changing the workflow.
Complete resolved execution mappings are mandatory; sparse Python callers must explicitly
compose settings. Aliases cannot silently override populated canonical parameters.

## Owned inputs and retained records

CSV dataset ownership, exact image manifests, fresh output routing and selected checkpoints
retain their existing contracts. Derived model/source/output values are inspectable.
Configured native options are passed unchanged. Native normalization is recorded separately;
an explicitly requested image size 906 is preserved even when execution uses a stride-compatible size.
Native owner-only training/validation previews are permitted. No extra tasks, checkpoint
duplicates, or weakened artifact/model failure handling; see the
[publication contract](../../008-dataset-clearml-tracking/contracts/publication.md).

## Migration

Regenerate old examples with cy-init-config into a new directory, then reapply explicit
choices. Prediction values no longer come from an implicit merge. Use weights or
ultralytics_predict.model for standalone inference. Remove unsupported/deprecated aliases
in favor of the installed canonical parameter. No dependency update is required.
