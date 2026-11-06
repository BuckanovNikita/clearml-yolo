# Multi-model and deployment acceptance

When detector integration changes, follow the
[multi-model acceptance guide](../../../../specs/000-baseline/spec.md#detector-backends-and-deployment-export)
and its backend/export contracts in addition to the shared workflow checks in the
[verification checklist](../SKILL.md#verification-checklist).

## Presets

- Exercise every advertised preset with real short training, pretrained initialization,
  best selection, standalone copied/downloaded checkpoint reload, prediction and validation.
- Use non-square images, exact string labels and empty-image records.
- Check one owner task, one best Output Model, descriptor/hash integrity, telemetry and
  required upload/flush failure behavior.
- Synthetic random-weight smoke tests establish execution only.

## Cross-family comparison

- Run new-family comparisons against YOLO and another native family on identical current
  images with frozen thresholds.
- Inspect independent backend routing, common device/settings, checkpoint-owned vocabulary
  and recorded effective preprocessing.
- Verify raw-reference assertions, cache separation and checkpoint/source conflicts.
- Repeat both execution paths (direct and queued), replay guards, mixed-family sweeps,
  cancellation and owned-process cleanup.

## Faster R-CNN ONNX/TensorRT

- For every Faster R-CNN preset and FP32/FP16, generate the actual ONNX graph, build the
  engine and execute all required size/batch cases, profile transitions, empty/crowded
  inputs and rejection cases.
- Separately execute in a fresh runtime without Torch or ClearML.
- Freeze labeled corpus/checkpoint bytes and actual evaluator source identity; require
  meaningful nonzero native mAP and the documented precision-specific mAP loss limits.
- Report preprocessing, class-aware detection matching, unavailable raw tensors, latency
  and scoped memory evidence separately.
- A quality report alone does not prove standalone execution or all numerical/scene cases.
- CUDA 11.8 deployment requires separate target evidence; a newer-CUDA local engine does
  not prove target compatibility.
