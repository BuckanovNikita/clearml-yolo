# ADR-0200 · Train detector families under one experiment contract

CY uses the same ground truth, experiment ownership and checkpoint handoff across detector families. The selected backend owns the training recipe, image geometry and interpretation of its native checkpoint. A downstream stage can therefore identify the model that produced its predictions without assuming that all detectors use YOLO conventions.

## Training inputs and failure policy

`cy-train` requires populated training and validation splits. It resolves the [ground truth source](0100-datasets.md#conversion-and-source-resolution), prepares the selected backend's [dataset layout](0100-datasets.md#native-layouts-and-cache-identity) and supplies the ordered classes, split and paths to the trainer. One task owns training and publication. The standalone command fails if a required checkpoint is missing or publication fails. The [pipeline](0001-experiment-workflows.md#pipeline-stages-and-outcomes) has its own policy for failures after successful training.

For non-YOLO detectors, explicit full weights initialize a new optimization run. Where the family accepts a separate backbone, explicitly supplied backbone weights take effect when full weights are absent, including with `pretrained=false`. The model guide describes that combination as training from scratch. Random initialization applies when neither file is supplied and automatic pretraining is off. With automatic pretraining on, CY prepares the full RF-DETR detector or the backbone needed by the other families. [Model guide](../docs/configuration/model.md) · [Documented discrepancy](https://linear.app/sip-ds-team/issue/SIP-344)

CY refuses resume and starts fresh optimizer and scheduler state. Out-of-memory and numerical errors propagate. The trainer cannot silently reduce the requested batch, change precision or compiler mode, or substitute a checkpoint. Choosing a batch for a later run belongs to [batch estimation](0220-batch-capacity.md#admission-and-measurement).

<details>
<summary>Sources and verification</summary>

- Run standalone training from ground truth — [Training command](../docs/commands/cy-train.md) · [Training workflow](../src/clearml_yolo/application/use_cases/train.py) · [CSV training boundary](../tests/test_train.py) · [Training finalization cases](../tests/test_training_success_finalization.py)
- Keep explicit training weights authoritative — [Detector contract](../DOCS.md#detector-families) · [Selected initialization inputs](../src/clearml_yolo/adapters/assets/execution.py) · [Backbone load](../src/clearml_yolo/adapters/torchvision/backbone.py) · [Full checkpoint load](../src/clearml_yolo/adapters/torchvision/training.py) · [Local weights and registry cases](../tests/test_model_assets_loading.py)
- Keep the requested training run intact on failure — [Ultralytics recovery policy](../src/clearml_yolo/adapters/integrations/native_trainer.py) · [OOM and configured batch cases](../tests/test_yolo_oom.py)

</details>

## Detector execution and best checkpoints

| Family | Training contract | Best checkpoint and inference |
| --- | --- | --- |
| Ultralytics YOLO | The default family uses an explicit effective detection model and the installed native trainer. CY classifies upstream keys as shared, training, prediction or inactive. An unknown key fails registration or measurement-profile construction. Inactive tiling keys are dropped, and CY retains its explicit NMS IoU when upstream supplies a null default. | `weights/best.pt`. Native detections are mapped to original-image coordinates. Generated YAML and the command use the same stage-specific projections. |
| DEIMv2 | The preset selects a solver from the [verified source tree](0213-model-assets.md#deimv2-source-and-large-backbones). Prepared COCO data supplies the class order. Training uses square images with sides of at least 128 pixels divisible by 32, and one gradient accumulation step. | Prefer `best_stg2.pth`, then `best_stg1.pth`. The native postprocessor rejects half precision and nondefault NMS IoU. Large presets have a separate [backbone preparation path](0213-model-assets.md#deimv2-source-and-large-backbones). |
| RF-DETR | The preset selects its native Lightning detector and square resolution divisible by 32. A full detector checkpoint initializes pretraining. A separate backbone checkpoint is unsupported. | `checkpoint_best_total.pth`. Prediction uses the stored vocabulary, confidence cutoff and detection limit. Half precision and nondefault NMS IoU are rejected. |
| Faster R-CNN | CY scales images to fit the canvas and pads on the right and bottom. ROI pooling uses the backbone strides, including for short images. The classifier reserves an internal background class. | `best.pth` by validation mAP50–95. CY maps foreground labels back to dataset classes. Inference supports class-aware NMS, CUDA half precision and the [deployment workflow](0230-model-deployment.md#exporting-the-model-and-its-inference-policy). |
| FCOS | The Torchvision head uses P3 through P7, one anchor size per level and a zero-based foreground vocabulary. It shares Faster R-CNN's letterbox canvas and prepared COCO input. | `best.pth` by validation mAP50–95. CY restores boxes to original-image coordinates. The descriptor identifies FCOS even if the two detectors share a backbone. |

Faster R-CNN and FCOS share AdamW, configurable gradient accumulation and strict loading of explicit detector weights. With exponential moving average enabled, validation evaluates the averaged model after each epoch. The trainer records loss and validation metrics and fails on non-finite loss. Inactive configuration groups cannot override the selected family's settings. [Detector settings](../docs/configuration/model.md)

<details>
<summary>Sources and verification</summary>

- Train and predict with Ultralytics YOLO — [Ultralytics training settings](../docs/configuration/ultralytics.md) · [Native training](../src/clearml_yolo/adapters/integrations/training.py) · [Prediction conversion](../src/clearml_yolo/adapters/yolo/inference.py) · [Native training outcomes](../tests/test_native_training_outcomes.py) · [YOLO memory failure cases](../tests/test_yolo_oom.py)
- Run DEIMv2 against its pinned upstream source — [Native solver and prediction](../src/clearml_yolo/adapters/deim/backend.py) · [Source validation](../src/clearml_yolo/adapters/deim/source.py) · [DEIMv2 contract cases](../tests/test_deim_backend.py) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443)
- Use the RF-DETR preset's full detector checkpoint — [RF-DETR training and prediction](../src/clearml_yolo/adapters/rfdetr/backend.py) · [Registry asset mapping](../src/clearml_yolo/adapters/rfdetr/assets.py) · [RF-DETR contract cases](../tests/test_rfdetr_backend.py)
- Preserve Faster R-CNN geometry on a padded canvas — [Faster R-CNN model](../src/clearml_yolo/adapters/fasterrcnn/model.py) · [Canvas transform](../src/clearml_yolo/adapters/torchvision/transform.py) · [Faster R-CNN contract cases](../tests/test_fasterrcnn_backend.py)
- Use FCOS with a zero-based foreground vocabulary — [FCOS model](../src/clearml_yolo/adapters/fcos/model.py) · [FCOS integration](../src/clearml_yolo/adapters/fcos/backend.py) · [FCOS head and label cases](../tests/test_fcos_backend.py)
- Classify the installed Ultralytics settings by stage — [Classification and projections](../src/clearml_yolo/adapters/yolo/config.py) · [Installed template and changed-default cases](../tests/test_native_config.py) · [Tiling and IoU compatibility decision](https://linear.app/sip-ds-team/issue/SIP-325) · [prediction settings](../docs/configuration/ultralytics-predict.md)
- Share the training recipe across Torchvision detectors — [Optimizer, EMA and checkpoint selection](../src/clearml_yolo/adapters/torchvision/training.py) · [Evaluation](../src/clearml_yolo/adapters/torchvision/evaluation.py)

</details>

## Augmentation across samples and workers

The default profile leaves native augmentation in charge. A custom Albumentations root Compose takes over optional training transforms while the detector keeps final resize, tensor conversion and normalization. The custom pipeline must preserve RGB images and box labels, including when a crop leaves no boxes. Validation and prediction keep their own preprocessing.

CY validates and freezes the pipeline, original source name and digest of canonical JSON into a snapshot. Workers and replay use that content even after the source file changes. A supplied snapshot whose content fails validation or whose digest disagrees is rejected. A single Mosaic may appear first in the root Compose. Its raw donor images and boxes come from the same training population, retaining each detector's class mapping. [Augmentation guide](../docs/configuration/transforms.md)

<details>
<summary>Sources and verification</summary>

- Apply custom augmentation only to training samples — [Albumentations pipeline](../src/clearml_yolo/adapters/augmentation/pipeline.py) · [Detector bridges](../src/clearml_yolo/adapters/augmentation/torch_data.py) · [Detector augmentation cases](../tests/test_detector_augmentation.py) · [YOLO augmentation cases](../tests/test_yolo_augmentation.py) · [Custom augmentation history](https://github.com/BuckanovNikita/clearml-yolo/commit/3b95fbaae4bc2440e239e7b01a3c47755475ac8f)
- Freeze the augmentation pipeline for workers and replay — [Snapshot resolution](../src/clearml_yolo/adapters/augmentation/configuration.py) · [Canonical digest and validation](../src/clearml_yolo/core/transforms.py) · [Snapshot and serialization cases](../tests/test_augmentation.py)

</details>

## Distributed execution and publication

When a non-YOLO training run selects multiple logical GPUs, the global batch must divide evenly among the supervised ranks. DEIMv2 uses NCCL, RF-DETR uses Lightning DDP, and the Torchvision families use distributed data sampling. A rank failure or deadline terminates the group. Prediction uses one device.

Only the invocation owner creates the task and publishes results. Native Ultralytics rank zero writes supported epoch and validation callbacks and their local artifacts to a run-owned journal. The owner replays it before finishing publication. CPU relay tests exercise event transport. Native multi-GPU execution and remote delivery require live evidence.

<details>
<summary>Sources and verification</summary>

- Keep distributed training under one invocation owner — [Training device selection](../docs/commands/cy-train.md) · [Supervised rank group](../src/clearml_yolo/adapters/integrations/distributed_training.py) · [Native callback relay](../src/clearml_yolo/adapters/integrations/native_ddp.py) · [Distributed configuration](../tests/test_distributed_configuration.py) · [CPU callback relay cases](../tests/test_native_ddp_cpu.py)
- Replay Ultralytics DDP callbacks in the owning process — [Owner replay integration](../src/clearml_yolo/adapters/integrations/training.py) · [Native relay cases](../tests/test_native_ddp.py)

</details>

## Checkpoint identity at handoff

A non-YOLO checkpoint embeds the family, preset, ordered classes and preprocessing. CY writes a companion descriptor bound to the resulting bytes by digest. On reload it recovers the embedded descriptor, checks any supplied companion and rejects a conflicting model selection. A legacy checkpoint without embedded metadata has no inferred descriptor.

The technical reference directs users to keep both model and identity sidecars with the checkpoint. The model reader can reconstruct the descriptor from the checkpoint alone. An absent identity sidecar leaves the identity unavailable, so a consumer may still require a label or provenance. [Detector contract](../DOCS.md#detector-families) · [Documented discrepancy](https://linear.app/sip-ds-team/issue/SIP-345)

<details>
<summary>Sources and verification</summary>

- Bind detector identity and class order to checkpoint bytes — [Training output](../docs/commands/cy-train.md) · [Descriptor writer and reader](../src/clearml_yolo/adapters/storage/checkpoint.py) · [Identity companion](../src/clearml_yolo/adapters/storage/identity.py) · [Copy, tampering and compatibility cases](../tests/test_checkpoint_descriptor.py)

</details>
