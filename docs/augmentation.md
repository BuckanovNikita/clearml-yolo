# Custom training augmentation

`cy-train` and the training stage of `cy` accept one standard Albumentations JSON
pipeline for every registered YOLO, DEIMv2, RF-DETR, Faster R-CNN and FCOS selection. FCOS support describes
unreleased source changes; native GPU acceptance remains pending.
The default `transforms=default` keeps each backend's native augmentation recipe.
Select `transforms=albumentations` to replace optional native augmentation with your
JSON. Prediction, validation and export keep their normal preprocessing.

## Save and select a pipeline

Create JSON with the installed Albumentations version:

```python
from pathlib import Path

import albumentations as A

pipeline = A.Compose(
    [A.HorizontalFlip(p=0.5), A.RandomBrightnessContrast(p=0.2)],
    bbox_params=A.BboxParams(
        format="pascal_voc",
        label_fields=["class_labels"],
        clip=True,
    ),
)
A.save(pipeline, Path("augmentation.json"))
```

Pass its filename alongside your ordinary training configuration:

```bash
cy-train model=rfdetr/nano ground_truth=./ground_truth.csv \
  transforms=albumentations transforms.pipeline_file=./augmentation.json \
  model.train.device=0 model.train.epochs=20 \
  clearml.project_name=detection clearml.task_name=rfdetr-custom \
  'clearml.tags=[rfdetr,custom-augmentation]'
```

The same two `transforms` overrides work with `model=ultralytics`, all four DEIMv2
presets, all four RF-DETR presets, all six Faster R-CNN presets and all six FCOS presets. Keep training
settings in `ultralytics.*` for YOLO or `model.train.*` for the other families.
For a complete experiment, use `cy` with the same overrides and a CSV containing
train, validation and test splits. See the [model guide](multi-model-backends.md).

The checked examples [flip.json](../examples/augmentation/flip.json) and
[mosaic.json](../examples/augmentation/mosaic.json) can be selected directly from a
source checkout. Inspect the composed settings without starting training:

```bash
cy-train model=rfdetr/nano transforms=albumentations \
  transforms.pipeline_file=./examples/augmentation/mosaic.json --cfg job
```

`--cfg job` displays Hydra composition; execution separately validates the JSON
contents. File paths are interpreted by the launching process. A missing or malformed
file fails before training; there is no fallback to native augmentation.

## Composition and conflict rules

The JSON root must be `Compose` in standard `A.save` format. Nested supported
compositions such as `OneOf` and `Sequential` retain their order and probabilities.
A missing bbox processor defaults to `pascal_voc` with `class_labels`.
Explicit `pascal_voc`, `coco`, `yolo` and `albumentations` box formats are supported;
the adapter converts raw absolute boxes into the chosen format and back. Specify
at most one class-label field. Box clipping and filtering settings are preserved,
and classes, instance identities and crowd flags remain aligned after filtering.
Images with no boxes, including crops that remove every box, remain valid samples.

Configuration checks reject:

- Unknown transform classes or constructor arguments, invalid probabilities and
  bbox-filter settings; errors identify the JSON location.
- `Normalize`, `ToFloat`, `FromFloat`, `ToTensorV2` and `ToTensor3D`, because the
  backend owns input scaling, normalization and tensor conversion.
- `Lambda`, external executable transforms, mask/keypoint/volume requirements,
  additional targets, and transforms that cannot preserve detection boxes or RGB input.
- Multiple, nested or non-first Mosaic transforms, and Mosaic metadata keys that
  collide with image, target or class-label fields.

Custom mode also applies visible backend-specific overrides. Explicit conflicting
native augmentation values are replaced with the disabled values and logged before
training. Invalid JSON settings are rejected rather than corrected silently.

| Backend | Optional native augmentation disabled in custom mode | Final model preparation retained |
| --- | --- | --- |
| YOLO | HSV, random affine/perspective, flips, BGR probability, native Mosaic/MixUp/CutMix/copy-paste, auto augmentation, erasing, multi-scale, close-Mosaic scheduling and native `augmentations` | Letterbox to the configured size, box formatting, RGB tensor layout and trainer scaling |
| DEIMv2 | Native image augmentation, Mosaic policy, batch MixUp/copy-blend and repeated-size scheduling | Resize, tensor conversion, normalization and native box conversion |
| RF-DETR | Native augmentation recipe, scale jitter and multi-scale | Deterministic native resize, tensor conversion and normalization |
| Faster R-CNN / FCOS | No optional native dataset augmentation is present | Tensor conversion and the detector's normal resize, padding and normalization |

Custom transforms consume raw RGB `uint8` images. You may include geometric
operations such as `Resize` or crops, but their output shape is followed by the
backend's required final geometry. Set `ultralytics.imgsz` or `model.train.imgsz`
to control the model's final size. A JSON resize does not change that setting.
Input scaling and normalization occur once at the backend boundary.

To return to native augmentation, select `transforms=default` and remove the JSON
selector and any saved custom snapshot. A file or snapshot in native mode is an
error. `model.train.augmentation` describes custom-mode overrides; it is not a
second user augmentation pipeline and is rejected in default mode.

## Mosaic on every model

Place one `A.Mosaic(...)` first in the root Compose, then add ordinary transforms:

```python
pipeline = A.Compose(
    [
        A.Mosaic(
            grid_yx=(2, 2),
            target_size=(640, 640),
            cell_shape=(640, 640),
            metadata_key="training_donors",
            p=0.5,
        ),
        A.HorizontalFlip(p=0.5),
    ],
    bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]),
)
A.save(pipeline, Path("mosaic.json"))
```

CY supplies the metadata automatically. Donors come only from the current training
population and are read without recursive augmentation. A grid with `rows * columns`
cells uses that product minus one donors. Other images are selected distinctly when
there are enough; small populations use replacement. The primary image is a donor
only when the entire training population contains one image. Empty primary/donor
images are supported. Native YOLO or DEIM Mosaic remains disabled, so JSON Mosaic
is not applied on top of another Mosaic implementation.

The configured training seed and data-worker seeds control the augmentation streams.
Each worker advances its stream between images; it does not reset the same random
transformation for every sample.

## Editable configurations and replay

`cy-init-config DIRECTORY --command cy-train --model rfdetr/nano` exports the command
wrapper, local `train.yaml` base, selected model, `transforms/default.yaml`,
`transforms/albumentations.yaml`,
and the selected model's `transform_overrides` files. The `cy` export includes the
same training profiles with local `pipeline.yaml`. Fresh trees contain every application
YAML referenced by their defaults. The root defaults select the specialization for the chosen
model/profile pair, making effective disabled values visible in `--cfg job` output.

Before execution or queue serialization, the selected JSON is validated and copied
into the canonical configuration as `transforms.snapshot`, with its SHA-256 digest
and original file selector. DDP workers and remote replay consume that frozen content
without requiring the source JSON file. A changed snapshot with a mismatched digest
fails validation. Editing the source file does not alter an existing snapshot;
a fresh invocation without a snapshot reads the file again, and selecting a different
file replaces the old snapshot. Keep the JSON under version control with the run
configuration for reviewable experiments.

Saved [batch estimates](batch-estimation.md) currently describe native augmentation
profiles. Custom Albumentations mode requires an explicit numeric training batch;
`batch=null` fails instead of reusing an estimate for a different augmentation recipe.

## Severstal execution checks

The opt-in [Severstal suite](../tests/test_severstal_gpu.py) covers every registered model:
YOLO26n, four DEIMv2, four RF-DETR, six Faster R-CNN and six FCOS presets, each with native,
JSON and JSON+Mosaic variants. Each smoke scenario uses one epoch, batch one and FP32
on a frozen 160/40/40 training/validation/test subset of the official Kaggle data.
They check execution, optimization, checkpoint reload, held-out predictions and
ClearML evidence; they do not establish model accuracy or equivalence between recipes.

The preparation tool requires the official `train.csv` and `train_images`, converts
one-based column-major masks into one box per 8-connected component, and retains
background images and the four literal classes. Source-content identities keep
duplicate images together in the seeded 80/10/10 split. See the
[feature requirements](../specs/004-custom-augmentation/spec.md) for acceptance scope.
These are required scenarios, not a claim that the matrix has passed. Execution
results belong in dated verification evidence.

Full-dataset training is a [separate follow-up](../specs/004-custom-augmentation/full-training-task.md)
requiring additional approval after feature release. Running the smoke suite does
not start that follow-up.
