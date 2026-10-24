# Custom augmentation quickstart acceptance

Generate a selected training configuration with cy-init-config, populate ground_truth,
model and explicit ClearML project/tags, then append:

```text
transforms=albumentations transforms.pipeline_file=./augmentations.json
```

The JSON is written with Albumentations A.save. Use a first top-level Mosaic for shared
multi-image augmentation. Review --cfg job output for disabled native values. Actual
execution additionally validates/freeze-loads the file and records overrides and hash.

Verify default and custom profiles across every preset, then run the opt-in Severstal
matrix against a prepared local official dataset. Read the task ledger for acceptance
requirements; configuration composition alone does not establish native outcomes.


## Run the native dataset suite

Prepare the official download first, retaining the frozen manifest:

```bash
uv run --frozen --no-sync python scripts/severstal.py prepare \
  --source /data/severstal/official --output /data/severstal/prepared
uv run --frozen --no-sync pytest tests/test_severstal_gpu.py \
  --run-severstal-gpu --severstal-dataset /data/severstal/prepared \
  --severstal-artifacts /work/severstal-checks \
  --severstal-clearml-project 'augmentation acceptance' \
  --severstal-tags augmentation-acceptance --severstal-device 0
```

These are smoke tests with one epoch, batch one, seed zero and FP32. They require
an available GPU, authenticated ClearML artifact storage and the selected preset's
native pretrained assets. Use an isolated owned project and follow the environment's
cleanup policy. Full training requires separate approval.

For gated or offline DEIM/Faster R-CNN backbones, append repeatable local-file
selectors to the same pytest invocation:

```text
--severstal-backbone deimv2/l=/models/dinov3_vits16_pretrain_lvd1689m-08c60483.pth
--severstal-backbone deimv2/x=/models/dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth
```

Each selector applies to that preset's default, JSON and Mosaic variants, preserving
its initialization across the comparison. Obtain the matching authorized native
weights; a URL, missing/empty file, duplicate preset or unsupported backend is rejected.
The override uses the ordinary `model.train.backbone_weights` interface. It does not
substitute random weights or bypass upstream access requirements.
