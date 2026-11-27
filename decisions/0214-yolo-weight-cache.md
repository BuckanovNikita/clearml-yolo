# ADR-0214 · Persist a stable Ultralytics weight-cache directory

Ultralytics can store its weight directory as a relative path. An estimator worker or later training invocation can start elsewhere and resolve that setting differently. During explicit preparation, automatic catalogue preparation or YOLO batch-estimator setup, CY resolves the original value against the working directory, persists the absolute path through the SDK and verifies the complete stored settings.

CY serializes this update among its callers and preserves unrelated persisted settings. Inert imports, help and configuration inspection do not perform this update. A write or readback failure is reported.

[Weight preparation guide](../docs/commands/cy-download-weights.md) · [Settings update and verification](../src/clearml_yolo/adapters/yolo/assets.py) · [Persistence and failure cases](../tests/test_yolo_weights_settings.py) · [Cache directory decision](https://github.com/BuckanovNikita/clearml-yolo/commit/597985fa39476b262bc05daa66ee3fb3e468724a)
