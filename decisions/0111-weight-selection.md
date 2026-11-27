# ADR-0111 · Resolve prediction weights and identify their source

## Context

An operator may provide a local checkpoint, an existing ClearML model or a native YOLO name. The result must carry a readable model identity.

## Decision

Use an existing file directly, resolve a task ID to its selected checkpoint, or fetch a `clearml://` model ID. Verify supplied hashes and recover identity from ClearML or a bound local identity sidecar. A filesystem-looking selector must name a file. A bare YOLO model name can reach the native backend.

## Consequences

A local model without recorded provenance requires a custom `model_label`. A label does not override an existing trusted identity. A directory or missing explicit path fails. A checkpoint changing during prediction fails the provenance check.

## Evidence

- [Selector and workflow checks](../src/clearml_yolo/application/use_cases/predict.py)
- [Model repository](../src/clearml_yolo/adapters/clearml/models.py)
- [Checkpoint identity sidecars](../src/clearml_yolo/adapters/storage/identity.py)
- [Selector and identity cases](../tests/test_model_identity_sources.py)
- [Prediction guide](../docs/commands/cy-predict.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#inputs)
