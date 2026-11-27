# ADR-0236 · Bound the engine's input shapes with optimization profiles

Faster R-CNN deployment accepts rectangular full frames and long image strips. Export metadata supplies a distinct min/opt/max TensorRT profile for each layout. Shapes are NCHW, with three channels, a bounded batch, and spatial sides divisible by 32. The builder installs the profiles and the runner checks the deserialized engine against the recorded bounds.

Serving selects a profile covering the requested input. Shapes outside all supported profiles fail. The verification operation exercises profile endpoints, transitions and out-of-profile inputs. Extending the supported shape range requires a compatible engine build and evidence for that range.

[Export command](../docs/commands/cy-export.md) · [Declared profile shapes](../src/clearml_yolo/core/export.py) · [Runner checks](../src/clearml_yolo/adapters/export/runtime.py) · [Verification cases](../src/clearml_yolo/adapters/export/verification.py) · [Profile validation cases](../tests/test_detector_export.py) · [Verification coverage cases](../tests/test_export_workflow.py)
