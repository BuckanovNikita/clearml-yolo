# ADR-0210 · Freeze the augmentation pipeline for workers and replay

An editable Albumentations file can move or change after a run starts. CY resolves its content into a validated snapshot containing the pipeline, the original source name and a SHA-256 over canonical JSON. Workers and replay consume the frozen content. A supplied snapshot must pass the same content checks.

Changing the source file after capture leaves that run's augmentation intact. Altering the stored pipeline without updating its digest fails validation. A source path by itself cannot reproduce a historical training transformation.

[Transforms configuration](../docs/configuration/transforms.md) · [Snapshot resolution](../src/clearml_yolo/adapters/augmentation/configuration.py) · [Canonical digest and validation](../src/clearml_yolo/core/transforms.py) · [Snapshot and serialization cases](../tests/test_augmentation.py)
