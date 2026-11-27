# ADR-0114 · Capture requested and effective inference settings

## Context

An image-size request can be normalized by the native backend. Results from two invocations with apparently identical parameters may also use different split membership or batching.

## Decision

[Prediction](0110-prediction.md) chooses the active family's settings, resolves the scoring size and writes an input manifest per group. Save native YAML before and after inference to distinguish requested settings from effective ones. Record meaningful native normalization along with model identity. The native `conf` cutoff filters raw predictions before [evaluation calibration](0131-calibration.md).

## Consequences

A reviewer can trace each split group to the images and settings actually used. The [YOLO native-settings contract](0217-native-yolo-settings.md) governs which upstream keys enter the request. YOLO's aggregate progress replaces its per-image console output. The native settings and backend-specific unsupported controls are documented with the owning configuration groups.

## Evidence

- [Per-group input and YAML capture](../src/clearml_yolo/application/use_cases/predict.py)
- [YOLO scoring size and inference settings](../src/clearml_yolo/adapters/yolo/inference.py)
- [Resolution and settings cases](../tests/test_predict.py)
- [YOLO prediction settings](../docs/configuration/ultralytics-predict.md)
- [Other backend settings](../docs/configuration/model.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#native-settings-and-quiet-output)
