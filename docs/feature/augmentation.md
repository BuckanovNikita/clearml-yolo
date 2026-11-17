# Augmentation

Training augmentation is selected by the `transforms` group of `cy-train` and the training
stage of `cy`. The default profile keeps each detector family's native augmentation. The
custom profile replaces optional native augmentation with one standard Albumentations JSON
pipeline, including an optional first Mosaic, that works the same way for every
registered YOLO, DEIMv2, RF-DETR, Faster R-CNN and FCOS preset. The pipeline is validated
before training and frozen into the run configuration, so replay and distributed ranks do
not need the source file. Prediction, validation and export always keep their normal
preprocessing.

## Behavior

### Profiles

- `transforms=default` keeps the native augmentation recipe of the selected family.
- `transforms=albumentations transforms.pipeline_file=FILE` applies the JSON pipeline to
  training images and visibly disables the family's optional native augmentation.
  Required final resizing, tensor conversion and normalization stay active.
- Custom transforms receive raw RGB `uint8` images and absolute boxes. Geometric
  transforms such as `Resize` or crops are allowed; the family's final geometry follows
  them. The model's final size is still set by `ultralytics.imgsz` or
  `model.train.imgsz`. Input scaling and normalization happen once, at the family
  boundary.
- Boxes are converted from raw absolute coordinates into the pipeline's box format and
  back. Classes, instance identities and crowd flags stay aligned after filtering. Images
  with no boxes, including crops that remove every box, stay valid samples.

### Native augmentation disabled in custom mode

| Family | Disabled settings | Final preparation kept |
| --- | --- | --- |
| YOLO (`ultralytics.*`) | `hsv_h`, `hsv_s`, `hsv_v`, `degrees`, `translate`, `scale`, `shear`, `perspective`, `flipud`, `fliplr`, `bgr`, `mosaic`, `mixup`, `cutmix`, `copy_paste`, `auto_augment`, `erasing`, `multi_scale`, `close_mosaic`, `augmentations` | Letterbox to the configured size, box formatting, RGB tensor layout and trainer scaling |
| DEIMv2 (`model.train.augmentation`) | `mosaic_prob`, `mixup_prob`, `copyblend_prob`, `base_size_repeat`, `ops` | Resize, tensor conversion, normalization and native box conversion |
| RF-DETR (`model.train.augmentation`) | `aug_config`, `augmentation_backend`, `scale_jitter`, `multi_scale` | Deterministic native resize, tensor conversion and normalization |
| Faster R-CNN, FCOS | No optional native dataset augmentation exists | Tensor conversion and the detector's resize, padding and normalization |

An explicit conflicting value is replaced with its disabled value and logged before
training as `Custom transforms override <group>.<key>: <requested> -> <disabled>`.
`model.train.augmentation` holds these family overrides; it is not a second pipeline.

### Mosaic

- One `A.Mosaic(...)` may appear as the first transform of the root `Compose`. CY supplies
  its donor metadata under the Mosaic `metadata_key`.
- Donors come only from the current training population and are read raw, without
  recursive augmentation. A grid of `rows * columns` cells uses that product minus one
  donors, chosen distinctly when the population is large enough and with replacement
  otherwise. The primary image is its own donor only when the population has one image.
  Empty primary and donor images are supported.
- Native YOLO and DEIMv2 Mosaic stay disabled, so JSON Mosaic never stacks on another
  Mosaic implementation.

### Reproducibility and replay

- The training seed and the data-loader worker seeds drive the augmentation streams. Each
  worker advances its stream between images rather than repeating one transformation.
- Before execution or queue serialization, the JSON is validated and copied into the
  canonical run as `transforms.snapshot` with its SHA-256 digest of canonical JSON and
  the original file selector. DDP ranks and remote replay use that snapshot.
- Editing the source file does not change an existing snapshot. A fresh invocation
  without a snapshot reads the file again, and selecting a different file replaces the
  old snapshot. Keep the JSON under version control with the run configuration.

## Configuration

- Save the pipeline with the installed Albumentations version using `A.save(pipeline,
  path)`. The document holds only `__version__` and `transform`; the root must be
  `Compose`. Nested compositions such as `OneOf` and `Sequential` keep their order and
  probabilities. Ready examples are [flip.json](../../examples/augmentation/flip.json)
  and [mosaic.json](../../examples/augmentation/mosaic.json).
- `bbox_params` belongs on the root `Compose` only. Without it, boxes use `pascal_voc`
  with label field `class_labels`. Formats `pascal_voc`, `coco`, `yolo` and
  `albumentations` are accepted, with exactly one class-label field. Clipping and
  filtering settings are applied as written.
- The file path is resolved by the launching process. `--cfg job` shows the composed
  profile and the disabled values without reading the JSON.
- `cy-init-config` exports `transforms/default.yaml`, `transforms/albumentations.yaml` and
  the selected model's `transform_overrides` files for training commands; see
  [commands and configuration](commands-and-configuration.md).
- An unset training batch reads the batch-size table without considering augmentation;
  choose a batch that suits the actual recipe. See [batch estimation](batch-estimation.md).

```bash
cy-train model=rfdetr/nano ground_truth=./ground_truth.csv \
  transforms=albumentations transforms.pipeline_file=./examples/augmentation/mosaic.json \
  model.train.device=0 clearml.project_name=detection clearml.task_name=rfdetr-custom \
  'clearml.tags=[rfdetr,custom-augmentation]'
```

## Failure behavior

Errors identify the JSON location, for example `transform.transforms[2]`. Validation
rejects, before any model asset or training starts:

- unknown or non-Albumentations transform classes, unknown constructor arguments,
  probabilities outside `[0,1]` and invalid box-filter settings;
- `Normalize`, `ToFloat`, `FromFloat`, `ToTensorV2` and `ToTensor3D`, because the family
  owns scaling, normalization and tensor conversion, and `Lambda`;
- `additional_targets`, `keypoint_params`, transforms that need non-image targets, spatial
  transforms without box support and outputs other than three RGB channels;
- a Mosaic that is nested, repeated or not first, and a Mosaic `metadata_key` that
  collides with image, box or class-label fields;
- an unreadable or malformed file: `Cannot read augmentation JSON <path>: …`. There is no
  fallback to native augmentation.

Profile errors:

- a pipeline file or snapshot with `transforms=default`: `Select transforms=albumentations
  before providing a pipeline`;
- `transforms=albumentations` without a file: `Albumentations requires pipeline_file or a
  resolved snapshot`;
- `model.train.augmentation` in the default profile: `model.train.augmentation requires
  transforms=albumentations`, and an override map for another family:
  `model.train.augmentation does not match the selected backend`;
- a snapshot whose digest does not match its content: `Transform snapshot sha256 does not
  match its pipeline content`.

## Limits

- Augmentation applies to training only.
- One pipeline per run; one Mosaic, first at the top level.
- Only built-in Albumentations classes are constructed; no executable code is loaded.
- Validation proves the pipeline constructs and runs on detection samples. It does not
  establish accuracy or equivalence between recipes.

## Code and tests

- [core/transforms.py](../../src/clearml_yolo/core/transforms.py) — profile selectors and
  snapshot identity.
- [entrypoints/hydra/transforms.py](../../src/clearml_yolo/entrypoints/hydra/transforms.py)
  — disabled native values and snapshot preparation.
- [adapters/augmentation/](../../src/clearml_yolo/adapters/augmentation/) — checked
  construction, Mosaic donors and seeded application.
- Family bridges:
  [yolo/augmentation.py](../../src/clearml_yolo/adapters/yolo/augmentation.py),
  [deim/transforms.py](../../src/clearml_yolo/adapters/deim/transforms.py),
  [rfdetr/transforms.py](../../src/clearml_yolo/adapters/rfdetr/transforms.py),
  [torchvision/data.py](../../src/clearml_yolo/adapters/torchvision/data.py).
- Tests: [test_augmentation.py](../../tests/test_augmentation.py),
  [test_transform_config.py](../../tests/test_transform_config.py),
  [test_hydra_transforms.py](../../tests/test_hydra_transforms.py),
  [test_detector_augmentation.py](../../tests/test_detector_augmentation.py),
  [test_yolo_augmentation.py](../../tests/test_yolo_augmentation.py).
- Verification limits: unit tests run pipelines on CPU samples; native GPU training with
  JSON and JSON+Mosaic recipes is established only by the live Severstal suite.
