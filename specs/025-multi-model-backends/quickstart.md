# Validation guide: Multi-model backends

This guide defines acceptance after implementation. Examples require the implemented
interfaces; their presence here is not evidence that commands or native tests have passed.
Follow [development procedures](../../docs/development.md) and the project
[end-to-end skill](../../.agents/skills/running-end-to-end-tests/SKILL.md). Keep machine
credentials, GPU capacity and task-owned resources in the applicable global environment
guidance. Use a dedicated ClearML project and explicit tags for every acceptance run.

## Prerequisites and local checks

- Install the selected optional backend/export dependencies; detector minimums are
  Torch >=2.13.0 and Torchvision >=0.28.0, locked at 2.14.1/0.29.1. Preserve the approved
  `digital-metrics`/`report-generator` copies and local overrides.
- Verify the approved DEIMv2 checkout and pretrained assets. Use existing permitted weight
  access; missing assets are an unmet gate, not permission to fake pretrained acceptance.
- Prepare a small labeled CSV with disjoint train/validation/test images, an empty image
  in every split, non-square examples and at least two classes. Use an additional fixed
  labeled quality corpus with meaningful detections for export comparison.
- Configure `CY_HOME` to a task-owned workspace and obtain ClearML access from maintained
  environment configuration. Preserve pre-existing shared workloads.

```bash
uv run --frozen --no-sync pytest
uv run --frozen --no-sync ruff check .
uv run --frozen --no-sync mypy .
uv run --frozen --no-sync lint-imports
uv run --frozen --no-sync cy-export --help
uv run --frozen --no-sync cy-init-config ./acceptance-config --command cy-train --model rfdetr/small
uv run --frozen --no-sync cy-train --config-dir ./acceptance-config --config-name cy-train --cfg job
```

Repeat help/configuration export for all model families and `cy-export`; confirm no task,
CUDA context or SDK import. Exercise default YOLO export, non-model commands, overwrite
refusal, symlinks and unrelated-file preservation.

## Native preset matrix

Use an explicit available device and small batch with the native recipe's short-run
controls. A representative command shape is:

```bash
uv run --frozen --no-sync cy-train model=rfdetr/small ground_truth=./acceptance/truth.csv \
  model.train.device=cpu model.train.epochs=1 \
  clearml.project_name=multi-model-acceptance clearml.task_name=rfdetr-small \
  'clearml.tags=[feature025,native-acceptance]'
```

Run the equivalent native training/reload/predict/validate/download sequence for every
preset in [the backend contract](contracts/backend.md), using its actual recipe and
required DEIMv2 `model.source_dir`. Verify finite losses/parameter updates, one chosen
best checkpoint, class mapping, checkpoint descriptor and effective configuration.
Use the returned/downloaded checkpoint in prediction and validation. Run `cy` with no
baseline to verify candidate-only reporting and later with a promoted baseline.

Freshly download the Output Model and every required artifact, then reload in a new
process. Verify canonical `gt_csv`/`predicts_csv`, exact validation threshold CSV, reports,
source lineage and one invocation task. Inspect owner-only telemetry and source-image
hashes/cache reuse. Inject callback, upload, flush and interruption failures and require
failed task completion with retained diagnostics.

## Scheduling, runtime ownership and cross-family comparison

For each backend, exercise `(queue.enabled, autogpu.enabled)` values `(true,true)`,
`(true,false)`, `(false,true)` and `(false,false)`. Check wait-before-task/SDK/CUDA,
automatic/exact device provenance and child remapping, CPU telemetry bypass, replay
admission restrictions, busy-to-free waiting, cancellation and descendant cleanup.
Verify reservation contraction only after owned training descendants exit.

Run mixed-family Hydra sweeps and inspect ordered results, concurrent queued admission,
sequential queue-off execution, per-run outputs/callbacks and failure propagation. Seed
normal home/user SDK configuration and external selectors; require them to remain
unchanged and discoverable through uploads/closure. Verify restored in-memory native
ClearML switches and fresh DDP callback scopes without settings-file writes. Project temp
callsites must use explicit paths while SDK temp defaults remain unchanged. Require retained
arenas after success, errors and cancellation, including overlapping and delayed children;
startup must perform no scan/recovery or recursive deletion. Invalid dataset entries must
remain preserved and native locks must fail without soft fallback. Preserve bounded optional
FiftyOne publication and process-cleanup receipts. Old local SDK settings/cache files remain
available only through explicit supported SDK selection, with no migration/deletion.

Compare each new backend against YOLO and another new backend using explicit source
checkpoints/thresholds or task IDs. Confirm one shared inference device, identical current
test membership, family-effective preprocessing evidence, unchanged threshold maps and
rejection of unsupported settings. Reports must consume the same evaluated pair.

## Faster R-CNN export acceptance

First prove ResNet-50 and DINO dynamic rectangular inference at batch four. Then repeat
for all six Faster R-CNN presets. Example operation separation:

```bash
uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn weights=./acceptance/best.pt \
  export.operation=onnx export.device=cpu output_dir=./acceptance/onnx \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-onnx \
  'clearml.tags=[feature025,export-acceptance]'

uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn export.operation=build \
  export.onnx=./acceptance/onnx/model.onnx export.device=0 export.precision=fp32 \
  output_dir=./acceptance/engine-fp32 \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-build \
  'clearml.tags=[feature025,export-acceptance]'

uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn export.operation=verify \
  weights=./acceptance/best.pt export.engine=./acceptance/engine-fp32/model.engine \
  ground_truth=./acceptance/quality-truth.csv export.device=0 export.precision=fp32 \
  output_dir=./acceptance/verify-fp32 \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-verify \
  'clearml.tags=[feature025,export-acceptance]'
```

Repeat FP16 build/verification. Metadata accompanies graph/engine inputs and must match
the source checkpoint. Execute all [export contract](contracts/export.md) shape/batch,
profile-transition, empty/crowded and rejection cases. Run the provided standalone
runner in a fresh environment without Torch or ClearML. Confirm proposals/ROI/NMS run
inside the engine and no fallback is used.

Freeze corpus/checkpoint/preprocessing/evaluator identity. Record raw/preprocessing
diagnostics where available and class-aware final detection matches. Require mAP50–95
loss at most 0.001 FP32 and 0.005 FP16, with per-class recall, finite outputs, correct
coordinate restoration and meaningful native detections. Record latency/memory and
limitations. Local newer-CUDA execution must not be labeled CUDA 11.8 target verification.

## Completion evidence

Record portable results and exact check commands in a dated feature verification report;
store machine paths, task IDs/logs and hardware observations in global environment evidence.
Mark every unexecuted gate accurately. Parent integration and final checks precede a
fresh independent read-only review. Validate changed Markdown, local links and generated
examples; execute applicable hooks and the authorized Git-tag-only release workflow.
No GitHub Release objects, package assets or registry uploads are permitted.
