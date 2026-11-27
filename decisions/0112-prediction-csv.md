# ADR-0112 · Represent detections in original pixels with explicit image naming

## Context

A table consumed by different detector backends and evaluators needs a single image identity convention and coordinate system.

## Decision

Write one row per detection with `image_name`, `instance_label`, `confidence`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br` and `bbox_y_br`. Use coordinates in original image pixels. Raw prediction supports `name`, `stem` and `path` naming. Evaluation joins canonical basenames from the ground truth.

## Consequences

An empty prediction output keeps all headers. Duplicate basenames cannot safely identify distinct images in `name` mode. Evaluators reject alternate naming modes recorded in provenance and reject image names outside the ground truth membership.

## Evidence

- [Stage-specific dataframe validation](0015-dataframe-validation.md)
- [Prediction data contract](../src/clearml_yolo/application/contracts.py)
- [Prediction assembly](../src/clearml_yolo/application/use_cases/predict.py)
- [Identity and membership validation](../src/clearml_yolo/core/evaluation/policy.py)
- [Inference cases](../tests/test_inference.py)
- [Prediction CSV format](../docs/formats/predictions.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#prediction-table)
