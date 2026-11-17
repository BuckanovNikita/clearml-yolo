# Detector families

CY trains, predicts, validates and compares five detector families behind one CSV, metric
and publication contract: Ultralytics YOLO, DEIMv2, RF-DETR, Faster R-CNN and FCOS. The
Hydra `model` group selects the family and preset for `cy`, `cy-train`, `cy-predict`,
`cy-val` and `cy-compare`; `cy-export` accepts Faster R-CNN presets only. Each family keeps
its native checkpoint, class, preprocessing and training semantics, and every checkpoint
that CY trains for a non-YOLO family carries an embedded descriptor that identifies it
wherever the file is copied.

## Behavior

### Families and presets

| `model=` | Architecture | Default training `imgsz` |
| --- | --- | --- |
| `ultralytics` (default) | Ultralytics model chosen by `ultralytics.model` | `ultralytics.imgsz` (960) |
| `deimv2/s`, `deimv2/m`, `deimv2/l`, `deimv2/x` | DEIMv2 DINOv3 S/M/L/X recipes at the approved source revision | 640 |
| `rfdetr/nano`, `rfdetr/small`, `rfdetr/medium`, `rfdetr/large` | RF-DETR Nano/Small/Medium/Large | 384, 512, 576, 704 |
| `fasterrcnn/resnet50_fpn`, `fasterrcnn/resnet101_fpn` | Torchvision ResNet-50/101 with FPN | 800 |
| `fasterrcnn/convnext_tiny`, `fasterrcnn/swin_tiny` | timm ConvNeXt-Tiny/Swin-Tiny with FPN | 800 |
| `fasterrcnn/dinov2_small`, `fasterrcnn/dinov3_small` | timm DINOv2/DINOv3 Small patch tokens with an explicit feature pyramid | 800 |
| `fcos/resnet50_fpn`, `fcos/resnet101_fpn` | ResNet-50/101 with a P3–P7 FPN | 800 |
| `fcos/convnext_tiny`, `fcos/swin_tiny` | ConvNeXt-Tiny/Swin-Tiny with a P3–P7 FPN | 800 |
| `fcos/dinov2_small`, `fcos/dinov3_small` | DINOv2/DINOv3 Small with P3–P7 feature pyramids | 800 |

These are fixed registered presets. Arbitrary timm backbone names and the original DEIM
family are not selections.

### Differences between families

- Faster R-CNN and FCOS train with AdamW, support gradient accumulation and EMA, and keep
  the checkpoint with the best validation COCO mAP50–95. DEIMv2 and RF-DETR keep their
  native best-checkpoint selection. YOLO keeps the Ultralytics trainer.
- FCOS has five P3–P7 pyramid levels with one square anchor per location and zero-based
  foreground labels. Faster R-CNN keeps an internal background class offset. They are
  distinct checkpoint architectures, and the background slot is never a public class.
- RF-DETR resolutions are square and divisible by 32. DEIMv2 dimensions are at least 128
  and divisible by 32, and DEIMv2 training needs a square size. Faster R-CNN and FCOS
  accept rectangular `[height,width]` canvases.
- DEIMv2 and RF-DETR use native DETR postprocessing without NMS; the `model.predict`
  controls and their per-family limits are listed in
  [prediction and validation](prediction-and-validation.md#native-prediction-controls).
- All families return boxes in original-image pixels with the exact CSV class strings.

### Checkpoint descriptors

- Every native checkpoint CY trains embeds a descriptor in its archive: backend, preset,
  ordered foreground class names, preprocessing, dependency versions and source revision.
  Native Torch readers ignore it, and it stays readable when the checkpoint is downloaded
  or copied alone.
- `<checkpoint>.model.json` records that descriptor with the checkpoint's SHA-256. When
  present, it must agree exactly with the embedded descriptor and the file hash.
- `<checkpoint>.identity.json` records the training task and model identity. Keep it next
  to the checkpoint when moving local files so standalone prediction can identify the
  source model.
- With a non-YOLO `model=` selection, weights must carry a descriptor whose family and
  preset match the selection; CY never loads them as another architecture. Comparing
  checkpoints without descriptors is covered by [comparison](comparison.md).

## Configuration

### Selecting a family

- Select a preset with `model=<family>/<preset>`; omit it for YOLO. YOLO settings live in
  `ultralytics` and `ultralytics_predict`; other families use the typed `model.train` and
  `model.predict` groups. `model.train` is described in [training](training.md).
- Changed settings in the inactive group are rejected in both directions, for example
  `Changed model.train settings [...] are inactive for ultralytics; use ultralytics
  instead` or `Changed ultralytics settings [...] are inactive for rfdetr/small; use
  model.train instead`.
- `model.source_dir` selects an explicit DEIMv2 source checkout and is rejected for other
  families.
- `cy-init-config DIR --command cy-train --model rfdetr/small` writes an editable tree for
  one preset; see [commands and configuration](commands-and-configuration.md).

### Initialization

| Family | `pretrained=true` without `weights` | `backbone_weights` | `weights` |
| --- | --- | --- | --- |
| DEIMv2 | Prepares the matching DEIMv2 backbone | Compatible local backbone | Native detector tuning with class-head adjustment |
| RF-DETR | Prepares the preset's pretrained detector | Rejected | Full native RF-DETR weights |
| Faster R-CNN, FCOS | Prepares the Torchvision/timm backbone; detection heads start new | Compatible local backbone state | Full detector state, loaded strictly |

Explicit `weights` or `backbone_weights` are used even with `pretrained=false`. Setting
`pretrained=false` with both paths `null` trains from random initialization. Asset
locations, caches and proxies are described in [model assets](model-assets.md).

### Prerequisites

- All families are part of the default installation; see [installation](installation.md).
- DEIMv2 needs its approved upstream source. With `model.source_dir=null`, execution
  prepares and verifies a managed copy; an explicit checkout must match the approved
  revision. DEIMv2 prediction also needs the source but never requests pretrained
  assets. RF-DETR requires its pinned SDK version.

## Failure behavior

- Unknown presets fail with `Unknown model preset: <family>/<preset>`.
- Missing packages, incompatible weights, unavailable pretrained assets and unknown
  settings fail. CY never substitutes another model or silently starts from random weights.
- A missing explicit weights file fails with `Explicit model weights do not exist: …`.
- RF-DETR `backbone_weights` fails with `RF-DETR backbone_weights is unsupported; use
  model.train.weights`.
- Faster R-CNN and FCOS full detector weights that do not match the architecture or
  class-head shape fail the strict load.
- A checkpoint descriptor or hash conflict fails before execution, for example
  `Checkpoint already has different detector metadata` or `Explicit model selection
  disagrees with the checkpoint descriptor`. Native weights without a descriptor fail with
  `Native detector weights require a bound checkpoint descriptor; raw comparison weights
  require explicit ModelRef metadata`.

## Limits

- Only the registered presets are supported.
- Training always starts a new run; optimizer and scheduler state are never resumed.
- Random initialization is suitable for smoke runs and says nothing about pretrained
  accuracy.
- MPS is not a supported cross-family target.
- Within one Python process, DEIMv2 runs sequentially with other families; programmatic
  callers that run families in parallel must use separate processes.
- `cy-export` supports Faster R-CNN only; see [export](export.md).

## Code and tests

- [core/models.py](../../src/clearml_yolo/core/models.py) — presets, typed controls and
  checkpoint descriptors.
- [integrations/detectors.py](../../src/clearml_yolo/adapters/integrations/detectors.py) —
  family routing and descriptor checks.
- Family adapters: [yolo](../../src/clearml_yolo/adapters/yolo/),
  [deim](../../src/clearml_yolo/adapters/deim/),
  [rfdetr](../../src/clearml_yolo/adapters/rfdetr/),
  [fasterrcnn](../../src/clearml_yolo/adapters/fasterrcnn/),
  [fcos](../../src/clearml_yolo/adapters/fcos/),
  [torchvision](../../src/clearml_yolo/adapters/torchvision/).
- [storage/checkpoint.py](../../src/clearml_yolo/adapters/storage/checkpoint.py) — embedded
  descriptors and `.model.json` records.
- Tests: [test_model_configs.py](../../tests/test_model_configs.py),
  [test_model_selection.py](../../tests/test_model_selection.py),
  [test_detector_integration.py](../../tests/test_detector_integration.py),
  [test_detector_workflows.py](../../tests/test_detector_workflows.py),
  [test_deim_backend.py](../../tests/test_deim_backend.py),
  [test_rfdetr_backend.py](../../tests/test_rfdetr_backend.py),
  [test_fasterrcnn_backend.py](../../tests/test_fasterrcnn_backend.py),
  [test_fcos_backend.py](../../tests/test_fcos_backend.py).
- Verification limits: unit tests run families on CPU with small inputs; native GPU
  training of each preset is established only by the live Severstal suite.
