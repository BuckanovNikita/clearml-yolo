# ADR-0211 · Draw mosaic donors from the current training population

A Mosaic transform requires other labeled images alongside the current sample. CY allows one Mosaic at the first position of the root Albumentations Compose. Its integration obtains raw donor images and boxes from the same training population, assembles the inputs in the required format, then lets the remaining pipeline transform the result.

This preserves each detector's class mapping and downstream preprocessing. Nesting a Mosaic or requesting a second one is rejected. Validation samples do not become donors.

[Transforms configuration](../docs/configuration/transforms.md) · [Mosaic execution](../src/clearml_yolo/adapters/augmentation/pipeline.py) · [Torch dataset bridge](../src/clearml_yolo/adapters/augmentation/torch_data.py) · [Donor and label cases](../tests/test_detector_augmentation.py) · [YOLO bridge cases](../tests/test_yolo_augmentation.py) · [Mosaic integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/3b95fbaae4bc2440e239e7b01a3c47755475ac8f)
