# Backend and command contract

This contract extends the existing [current contracts](../../../docs/current-contracts.md)
only for the approved model families. Existing YOLO behavior remains authoritative.

## Model selection

The model Hydra group selects the backend and preset. The default is `model=ultralytics`.
New-family groups own `backend`, `preset`, optional `source_dir` and validated `train` and
`predict` settings. Requested devices are `model.train.device` and `model.predict.device`.
The default YOLO group leaves top-level `ultralytics` and `ultralytics_predict` authoritative,
including native defaults, comments and explicit-null/default-value precedence.
Changed settings in either inactive family are rejected before admission: native selections
reject changed YOLO groups, and YOLO rejects changed `model.train`/`model.predict` values.
Unchanged schema defaults remain available for initial mixed-sweep composition.

| Group values | Backend | Presets |
| --- | --- | --- |
| `deimv2/s`, `deimv2/m`, `deimv2/l`, `deimv2/x` | DEIMv2 | Official S/M/L/X native recipes |
| `rfdetr/nano`, `rfdetr/small`, `rfdetr/medium`, `rfdetr/large` | RF-DETR | Native detection models |
| `fasterrcnn/resnet50_fpn`, `fasterrcnn/resnet101_fpn` | Faster R-CNN | ResNet FPN backbones |
| `fasterrcnn/convnext_tiny`, `fasterrcnn/swin_tiny` | Faster R-CNN | Hierarchical feature pyramids |
| `fasterrcnn/dinov2_small`, `fasterrcnn/dinov3_small` | Faster R-CNN | Explicit patch-feature pyramids |

`cy`, `cy-train`, `cy-predict`, `cy-val` and `cy-compare` retain their existing inputs,
output routing and ClearML ownership. Native selection/settings are validated before use;
unsupported values are errors. Missing optional packages/source/weights identify the
selected backend and actionable missing prerequisite without initializing another backend.

Local configuration export becomes:

```text
cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]
```

Omitted command still selects only `cy`. Omitted model retains the existing YOLO output
inventory. A selected new-family model exports its wrapper and required model group only.
`cy-export` is a valid command selection, defaulting to Faster R-CNN ResNet-50-FPN.
All destinations are preflighted before writing; existing selected files require explicit
replacement; symlink protections and unrelated-file preservation remain unchanged.
No configuration/help operation imports a native SDK or creates a ClearML task.

## Data and native operations

CSV ground truth remains mandatory for training. Validation, split semantics, source
immutability and canonical output columns remain unchanged. Derived COCO data and typed
Faster R-CNN records preserve empty images, exact class strings, original coordinates and
image membership. Output format and class mapping participate in cache identity.

Backends implement native train, load/reload, predict, requested/effective settings,
training resolution, vocabulary and inference evidence through project-owned ports.
The composition root selects them lazily. Prediction emits the existing canonical columns:
`image_name`, `instance_label`, `confidence`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`,
`bbox_y_br`. Scientific validation and evaluation remain backend-neutral.

Training records its actual native recipe in local YAML and sanitized owner `General`
parameters before model publication. New-family replay uses canonical `run.model`;
the owner reads the remote object explicitly, detaches SDK proxy containers and stores
sanitized snapshots without applying redaction to executable settings. An absent remote
object falls back to invocation inputs; a present empty or nonmapping object fails.
Observed `General` values cannot override executable settings or the inactive YOLO group.
A recording failure fails the invocation before model publication. One selected best checkpoint is
bound to a descriptor containing backend, preset, class mapping, preprocessing, revision
and hash. One owner task publishes one best Output Model and waits for upload/flush.
Workers relay events to the owner and never create tasks or publish independently.
Native callback/upload/interruption failures fail the invocation and retain diagnostics.

## Checkpoint resolution and comparison

Project descriptors survive local loading and ClearML download; a mismatch fails before
inference. Older project checkpoints remain YOLO. `ModelRef` accepts explicit `backend`
and `preset` overrides for raw external checkpoints that cannot otherwise be identified.
These overrides cannot replace a conflicting validated descriptor. Two references to
the same checkpoint must agree on resolved backend, preset, vocabulary and preprocessing;
display labels and thresholds remain independent. Existing threshold recovery and model
source selection retain their maintained contract.

Candidate and baseline resolve independently. Both receive the same current images,
requested inference/evaluation settings and one shared device. Backend-effective image
dimensions/preprocessing are recorded separately. Unsupported requested native settings
fail rather than disappearing. Prediction cache identity includes the backend/preset,
descriptor/preprocessing and shared image/settings identity.

Candidate thresholds are calibrated on validation only and frozen for test; baseline
thresholds are loaded unchanged. Canonical CSVs, reports, comparison statistics and pinned
evaluation algorithms remain unchanged. Optional missing automatic baseline behavior remains.
Developer/business report input adapters preserve exact text class labels, including
leading zeros and literal `NA`, while excluding numeric threshold footer cells. Eligibility
filters still apply and retain excluded classes explicitly; dependency sources are unchanged.

## Scheduling and isolation

Lightweight train/predict/export phase descriptions identify enabled work, device setting
paths and derived demand without importing SDKs. They feed existing supervisor, worker,
queue, Hydra launcher and replay logic. The four queue/autogpu combinations retain their
released behavior, exact identity/order, child-local remapping and provenance.

CPU execution bypasses GPU telemetry. Native pass-through with both controls false leaves
settings intact. Mixed-family queued sweeps retain ordered results and concurrent admission;
queue-disabled sweeps use sequential BasicLauncher; invalid mixed modes fail before admission.

Generic runtime isolation spans the whole invocation and final uploads. Select only the
required backend integration after admission. Finish/reap owned training descendants before
memory cleanup or reservation contraction. Bounded FiftyOne workers, cancellation and
task-owned cleanup remain unchanged; preserve unrelated services and durable data.
