# Native detector backends

The model group selects Ultralytics YOLO, DEIMv2, RF-DETR or Faster R-CNN for
`cy`, `cy-train`, `cy-predict`, `cy-val` and `cy-compare`. These commands share CSV
inputs, prediction records, calibration, evaluation, comparison and ClearML ownership.
The default remains `model=ultralytics`, with its existing `ultralytics` and
`ultralytics_predict` groups.

This guide documents the implemented interfaces. Configuration examples are not execution evidence.
Use the [verification ledger](../specs/025-multi-model-backends/verification.md) for
observed results and the [acceptance guide](../specs/025-multi-model-backends/quickstart.md)
for the required checks. The [backend contract](../specs/025-multi-model-backends/contracts/backend.md)
defines the shared behavior.

## Installation and model selection

Use Python `>=3.12.13,<3.14` and the approved external dependency copies described in
[development setup](development.md#external-dependencies). Keep those revisions and local
source overrides intact. From the project checkout, install the optional detector stack:

```bash
uv sync --frozen --extra detectors
```

The `detectors` extra requires Torch >=2.13.0 and Torchvision >=0.28.0; the committed
lock selects Torch 2.14.1 and Torchvision 0.29.1. It also supplies RF-DETR training,
timm and COCO evaluation dependencies declared in `pyproject.toml`. DEIMv2 additionally
needs its verified source checkout below. For ONNX export and its checks, add `--extra export`:

```bash
uv sync --frozen --extra detectors --extra export
```

The export extra supplies ONNX and ONNX Runtime. TensorRT and its matching CUDA runtime
are separate deployment prerequisites; see the [TensorRT deployment guide](tensorrt-deployment.md).
No model SDK or ClearML task is initialized by configuration export or composition.

| `model=` selection | Architecture | Default training `imgsz` |
| --- | --- | --- |
| `ultralytics` | Existing Ultralytics model selection through `ultralytics.model` | Existing `ultralytics.imgsz` |
| `deimv2/s`, `deimv2/m`, `deimv2/l`, `deimv2/x` | Pinned official DEIMv2 DINOv3 S/M/L/X recipes | 640 |
| `rfdetr/nano` | RF-DETR Nano | 384 |
| `rfdetr/small` | RF-DETR Small | 512 |
| `rfdetr/medium` | RF-DETR Medium | 576 |
| `rfdetr/large` | RF-DETR Large | 704 |
| `fasterrcnn/resnet50_fpn`, `fasterrcnn/resnet101_fpn` | Torchvision ResNet-50/101 with FPN | 800 |
| `fasterrcnn/convnext_tiny` | timm ConvNeXt-Tiny with FPN | 800 |
| `fasterrcnn/swin_tiny` | timm Swin-Tiny with FPN | 800 |
| `fasterrcnn/dinov2_small`, `fasterrcnn/dinov3_small` | timm Small patch-token backbones with explicit feature pyramids | 800 |

These are fixed registered presets. Arbitrary timm names and the original DEIM family
are not model selections. Missing packages, incompatible weights, unavailable pretrained
assets and unknown settings produce errors; the adapter does not substitute another model
or silently start from random weights.

## Editable configuration and commands

Generate only the selected command wrapper and model file:

```bash
cy-init-config detector-config --command cy-train --model rfdetr/small
cy-train --config-dir detector-config --config-name cy-train --cfg job
```

This writes `detector-config/cy-train.yaml` and
`detector-config/model/rfdetr/small.yaml`. Edit the latter's `train` and `predict`
sections, retaining `backend` and `preset`. Set the CSV and ClearML project, task name
and tags in the wrapper. `--cfg job` composes configuration without executing a model.
Existing selected files require `--force`; unrelated command files are preserved.

Without `--model`, configuration export keeps the existing YOLO layout. `cy-export`
defaults to `fasterrcnn/resnet50_fpn`. Commands that consume only tables, such as
`cy-metrics` and `cy-report`, do not accept a detector selection in `cy-init-config`.

For a direct RF-DETR pipeline run with automatic GPU admission:

```bash
cy model=rfdetr/small ground_truth=./ground_truth.csv \
  model.train.epochs=20 model.train.batch=4 model.train.device=-1 \
  model.predict.batch=2 model.predict.device=-1 \
  clearml.project_name=detection clearml.task_name=rfdetr-small \
  'clearml.tags=[rfdetr,experiment]'
```

For Faster R-CNN training and separate prediction from its selected checkpoint:

```bash
cy-train model=fasterrcnn/convnext_tiny ground_truth=./ground_truth.csv \
  model.train.epochs=20 model.train.device=-1 \
  clearml.project_name=detection clearml.task_name=convnext-train \
  'clearml.tags=[fasterrcnn,experiment]'

cy-predict model=fasterrcnn/convnext_tiny weights=./best.pth \
  ground_truth=./ground_truth.csv model.predict.device=cpu \
  clearml.project_name=detection clearml.task_name=convnext-predict \
  'clearml.tags=[fasterrcnn,predict]'
```

Use the actual returned checkpoint path. When copying weights, preserve the identity
sidecar described below. Inputs without training provenance require an explicit
`model_label` for standalone prediction/validation. For a CPU pipeline, set both
`model.train.device=cpu` and `model.predict.device=cpu`.

### DEIMv2 source and initialization

DEIMv2 loads its source privately from `model.source_dir`. Prepare a separate checkout:

```bash
git clone https://github.com/Intellindust-AI-Lab/DEIMv2.git ./vendor/DEIMv2
git -C ./vendor/DEIMv2 checkout 1d2ca42171570c713e78fc6a766ec5104b7f4724
```

The loader checks this exact revision and rejects changed or untracked files under
`engine/` or `configs/`. Git must be available. Keep pretrained assets outside those
source directories. A current branch checkout is not interchangeable with the pinned recipe.

Pretrained DEIMv2 training requires an explicit compatible full detector checkpoint or
backbone asset. For example, after obtaining the matching S backbone asset:

```bash
cy-train model=deimv2/s model.source_dir=./vendor/DEIMv2 \
  ground_truth=./ground_truth.csv model.train.device=-1 model.train.epochs=20 \
  model.train.backbone_weights=./weights/deimv2-s-backbone.pth \
  clearml.project_name=detection clearml.task_name=deimv2-s \
  'clearml.tags=[deimv2,experiment]'
```

The asset name above is a local example, not a downloadable model identifier.
`model.train.weights=./weights/deimv2-s-detector.pth` instead uses native detector tuning
with a compatible backbone and native class-head adjustment. DEIM prediction also needs
the verified `source_dir`; it loads the selected checkpoint without pretrained initialization.

## Training and prediction controls

New backends use validated `model.train.*` and `model.predict.*` keys. YOLO continues
to use `ultralytics.*` and `ultralytics_predict.*`. Changed `model.train.*` or
`model.predict.*` values are rejected when YOLO is selected; for example, use
`ultralytics.epochs=20` for YOLO training. CSV class names, image membership and split
assignments remain authoritative under the shared dataset policy.

When a new backend is selected, changed `ultralytics.*` or `ultralytics_predict.*`
values fail before admission. Put those settings in the selected model's typed groups;
legacy defaults may remain in the composed configuration. Mixed comparisons also reject
YOLO-only population controls, such as class filters, that a native backend cannot honor.

| Training key | Default | Meaning |
| --- | --- | --- |
| `epochs`, `batch`, `workers` | 100, 4, 4 | Native training duration, batch size and data workers |
| `imgsz` | Preset table above | Integer square size, or supported `[height,width]` pair |
| `device` | `null` | Device request handled by the selected execution mode |
| `lr`, `weight_decay`, `seed` | 0.0001, 0.0001, 0 | Optimizer controls and native seed |
| `pretrained` | `true` | Request pretrained initialization when no full weights are supplied |
| `weights`, `backbone_weights` | `null` | Explicit compatible detector or backbone file |
| `amp`, `use_ema` | `true`, `true` | Native mixed precision and exponential moving average |
| `grad_accum_steps` | 1 | Gradient accumulation; DEIMv2 currently requires 1 |

RF-DETR supports full native `weights`, or downloads its preset pretrained detector into
the run when `pretrained=true` and no weights are supplied. It rejects `backbone_weights`.
Faster R-CNN uses Torchvision/timm pretrained backbones with task-specific detection heads;
`backbone_weights` selects a compatible local backbone state, and `weights` loads a full
detector state strictly. Full detector weights must match the architecture and class-head
shape. Faster R-CNN uses AdamW, supports gradient accumulation and EMA, and selects its
best checkpoint by validation COCO mAP50–95. RF-DETR and DEIMv2 retain their native best
checkpoint selection.

Explicit `weights` or supported `backbone_weights` are still used when `pretrained=false`.
To request random initialization, set `pretrained=false` and leave both paths null.
That is useful for a smoke run but does not establish pretrained accuracy. This interface
starts a new training run; it does not resume optimizer or scheduler state.

| Prediction key | Default | Meaning |
| --- | --- | --- |
| `device`, `batch` | `null`, 1 | Shared inference device and batch size |
| `imgsz` | `null` | Use checkpoint preprocessing size for standalone inference |
| `conf`, `iou`, `max_det` | 0.001, 0.7, 300 | Prediction filtering, supported NMS control and detection limit |
| `half` | `false` | Faster R-CNN CUDA autocast; unsupported for DEIMv2/RF-DETR |

DEIMv2 and RF-DETR use native DETR postprocessing without NMS. They reject nondefault
`iou` and `half=true`. RF-DETR requires a square integer resolution divisible by 32.
DEIMv2 dimensions must be at least 128 and divisible by 32; training additionally
requires a square size. Faster R-CNN supports rectangular canvases, rounding dimensions
up to stride 32, preserving aspect ratio and padding on the right/bottom in normalized
RGB space. All adapters return boxes in original-image pixel coordinates and exact
foreground class strings. Faster R-CNN's internal background offset is never a public class.

The pipeline and paired comparison resolve shared requested inference settings before
scoring; recorded effective sizes can differ across backends. Predictions' `conf` is a
raw filtering threshold, separate from validation-calibrated class thresholds.

### Devices, scheduling and replay

New adapters currently support CPU and a single CUDA device. Multi-device requests
fail explicitly; the existing Ultralytics DDP behavior does not imply native DDP support
for these adapters. MPS is not an accepted cross-backend execution target in this guide.

Direct commands pass `model.train.device` and `model.predict.device` to the native
backend without admission, waiting or remapping. Use `cy-queue submit --gpus 1 -- ...`
to schedule a complete pipeline. The [queue](queue.md) supplies the allocated device
to GPU phases and preserves explicit CPU phases. Comparison uses one shared inference
device for both models. The former `queue.*` and `autogpu.*` settings are rejected.

Queue snapshots preserve resource requests and validate installation identity before execution.
A replay that changes between Ultralytics and a new-backend runtime is rejected: relaunch
with the matching `model=` selection. Changes between new-backend presets retain the
generic detector runtime but still undergo model and resource validation.

## Data, checkpoints and comparison

Keep the existing [ground-truth CSV contract](../specs/004-ground-truth-training/contracts/cli.md).
The new backends prepare cached COCO datasets automatically, including when the historical
Python API default says `dataset_format="ndjson"`. The cache retains empty images, exact
class names, split membership and original geometry. It does not convert existing YOLO
training into a COCO path. Training requires train/validation data; the complete pipeline
also uses the current test split.

Native training publishes one selected best Output Model under the invocation's ClearML
task. The checkpoint archive embeds backend, preset, ordered class vocabulary, preprocessing
and dependency/source metadata. `<checkpoint>.model.json` records that descriptor with
the final checkpoint hash. The embedded metadata remains readable when a checkpoint is
downloaded alone; any present descriptor sidecar must agree exactly. Keep
`<checkpoint>.identity.json` for training task/model identity when moving local files,
and `<predictions.csv>.provenance.json` with exported predictions. A hash or descriptor
conflict fails instead of selecting a different architecture.

Without explicit native `ModelRef` assertions, existing checkpoints without detector
metadata retain YOLO routing. A comparison binds
candidate and baseline independently, so a described Faster R-CNN baseline can be compared
with an RF-DETR candidate. Both run on the current split with shared inference settings;
baseline thresholds remain frozen and candidate calibration uses validation only.
Settings that a selected backend cannot honor fail explicitly.

For raw external native weights used by comparison, supply a `ModelRef` with `backend`,
`preset`, the full ordered foreground vocabulary, and correct `preprocessing`. A backend
name alone cannot identify the checkpoint's label order. For example, this fragment belongs
in a generated `cy-compare.yaml` wrapper:

```yaml
baseline_model:
  source: local
  weights: ./weights/external-fasterrcnn.pth
  thresholds: {thing: 0.4}
  label: external-fasterrcnn
  backend: fasterrcnn
  preset: resnet50_fpn
  class_names: [thing]
  preprocessing:
    resize: letterbox
    size: 800
    mean: [0.485, 0.456, 0.406]
    std: [0.229, 0.224, 0.225]
    stride: 32
    color: RGB
```

Replace the vocabulary, thresholds and preprocessing with the checkpoint's actual values.
The example requires a compatible full Faster R-CNN state; metadata does not convert an
arbitrary external architecture. Use `candidate_model` for the other side, and
`compare.baseline_model`/`compare.candidate_model` inside `cy` configuration. Explicit
metadata is asserted against an embedded descriptor when one exists. For a raw DEIMv2
reference, also supply its verified `source_dir` (or select it in the DEIM model group).
If both sides reference the same checkpoint, its resolved model metadata must agree.
Different display labels and class thresholds remain valid.

The same complete assertions work for ClearML task references: set `source: clearml`,
replace `weights` with the actual `task_id`, and retain the backend, preset, vocabulary
and preprocessing fields. Explicit thresholds remain valid; when omitted, comparison
recovers the task's frozen thresholds. Downloaded raw checkpoint bytes are not modified,
so later raw-file references still need their assertions. Conflicting embedded metadata
or recorded checkpoint hashes remain errors. Direct task/model-URI downloads without
these `ModelRef` assertions still require embedded detector metadata for `.pth` and `.ckpt`.

## Faster R-CNN export

`cy-export` supports Faster R-CNN presets with operations `onnx`, `build` and `verify`.
ONNX generation defaults to CPU/FP32; build and verification require an explicit GPU
request. Keep artifacts with their metadata sidecars. The separate deployment runner
does not create a ClearML task or require Torch.

Use the [deployment guide](tensorrt-deployment.md) for commands, dynamic profiles,
preprocessing, dependencies and quality gates. Successful composition or engine building
alone does not establish native parity, labeled-corpus accuracy or deployment portability.

## ClearML reporting transport errors

If Linux startup fails inside `Task.query_tasks` because `tasks` is `None`, preserve the
failed invocation and its logs. A response for another API endpoint requires transport
diagnosis; an empty task list alone does not establish this problem. The
[dated investigation](../specs/025-multi-model-backends/verification.md#clearml-reporting-transport-investigation--2026-10-12)
records a reproduced inherited-connection failure and its limits.

The ClearML SDK supports thread-based reporting through this setting in its HOCON
configuration, read before SDK initialization:

```hocon
sdk.development.report_use_subprocess = false
```

This is a ClearML SDK setting, not a Hydra override. Select `CLEARML_CONFIG_FILE` through
normal SDK configuration; external paths are valid and the application leaves the selector
unchanged. Preserve existing API settings and credentials, or supply them through the
established environment. Changing the reporting worker leaves the
application's queue, GPU admission and native model workers under their existing contracts.
Retry into a fresh output directory and require the normal publication checks to pass.
