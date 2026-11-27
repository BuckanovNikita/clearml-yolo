# ADR-0303 · Attach calibrated thresholds only to the matching owned model

A threshold artifact has scientific meaning for a specific checkpoint. A standalone metrics run may consume predictions from another experiment.

**Decision.** After [threshold calibration](0131-calibration.md), CY requires a model verified in this invocation, `val` calibration and a prediction provenance digest equal to the owned checkpoint SHA-256. It validates class names and finite confidence values, writes the mapping, per-class values, split and digest as metadata, and reads them from a fresh model handle.

**Consequences.** Consumers can associate thresholds with the exact owned model. Missing or conflicting provenance prevents the update. Standalone metrics can publish threshold artifacts without changing someone else's Output Model.

[Metadata validation and readback](../src/clearml_yolo/adapters/clearml/native.py) · [Pipeline calibration call](../src/clearml_yolo/application/use_cases/pipeline.py) · [Model protocol tests](../tests/test_clearml_native.py) · [Published model metadata](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b)
