# ADR-0208 · Apply custom augmentation only to training samples

The native transforms profile leaves the detector's own training pipeline in charge. Selecting Albumentations enables a validated root Compose for image and bounding-box transformations. CY disables overlapping optional native augmentation and leaves the backend responsible for final resizing, tensor conversion and normalization.

Validation and prediction retain their native preprocessing. The custom pipeline must preserve RGB images and box labels, including a crop that leaves zero boxes. CY rejects unsupported transforms and configuration before using the pipeline.

[Transforms configuration](../docs/configuration/transforms.md) · [Albumentations pipeline](../src/clearml_yolo/adapters/augmentation/pipeline.py) · [Detector bridges](../src/clearml_yolo/adapters/augmentation/torch_data.py) · [Detector augmentation cases](../tests/test_detector_augmentation.py) · [YOLO augmentation cases](../tests/test_yolo_augmentation.py) · [Custom augmentation history](https://github.com/BuckanovNikita/clearml-yolo/commit/3b95fbaae4bc2440e239e7b01a3c47755475ac8f)

See [augmentation snapshots](0210-augmentation-snapshot.md) and [mosaic donors](0211-mosaic-augmentation.md).
