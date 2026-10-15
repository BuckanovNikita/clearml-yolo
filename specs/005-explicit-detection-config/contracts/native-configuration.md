# Native Configuration Contract

This contract governs the default `model=ultralytics` selection. The approved
[multi-model amendment](../../025-multi-model-backends/contracts/backend.md) adds
independent typed `model.train`/`model.predict` groups for DEIMv2, RF-DETR and Faster
R-CNN, while retaining the YOLO defaults and precedence below. Export configuration
is governed by the [Faster R-CNN export contract](../../025-multi-model-backends/contracts/export.md).
With a new backend selected, changed settings in either inactive YOLO group fail before
admission; use the selected model's typed groups instead. Unchanged composed YOLO defaults
remain compatible. Mixed comparison dispatch rejects unsupported population overrides
rather than applying different filters to the two models.
With YOLO selected, changed `model.train` or `model.predict` values likewise fail before
admission; use `ultralytics` or `ultralytics_predict` respectively. Unchanged model schema
defaults support mixed-sweep composition without configuring the YOLO trainer or predictor.

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
weights or explicit ultralytics_predict.model provide model. No training-model fallback.

## Validation and filtering

Known detection-irrelevant settings remain commented and are omitted from execution.
Unknown keys and non-null cfg fail ordinary strict validation. Non-detect task, wrong stage mode,
non-null embed and invalid image size fail rather than silently changing the workflow.
Complete resolved execution mappings are mandatory; sparse Python callers must explicitly
compose settings. Aliases cannot silently override populated canonical parameters.

## Owned inputs and retained records

CSV dataset ownership, exact image manifests, fresh output routing and selected checkpoints
retain their existing contracts. Derived model/source/output values are inspectable.
Configured native options are passed unchanged. Native normalization is recorded separately;
an explicitly requested image size 906 is preserved even when execution uses a stride-compatible size.
The GPU queue supersedes the unchanged-device part of that rule: requested `device` remains in the
requested record, while an admitted fresh child receives concrete child-local device indices in
its effective record. Queue demand is derived from the requested native value; there is no separate
GPU-count setting. Other configured native options retain the unchanged/normalization behavior.
Native owner-only training/validation previews are permitted. No extra tasks, checkpoint
duplicates, or weakened artifact/model failure handling; see the
[publication contract](../../008-dataset-clearml-tracking/contracts/publication.md).

## Current configuration examples

Generate complete examples with cy-init-config into a new directory, then apply explicit
choices. Prediction values come only from the resolved prediction group. Use weights or
ultralytics_predict.model for standalone inference. Use the installed canonical parameter
names. No dependency update is required.

## Cross-contract integration

Default YOLO model commands use complete top-level `ultralytics` and `ultralytics_predict`
groups. Prediction reads its resolved group; visible references provide inheritance.
Raw wrapper `cfg`, non-null native `cfg`, nested stage-native mappings and duplicate
native comparison inference fields are unsupported and fail ordinary strict validation.
