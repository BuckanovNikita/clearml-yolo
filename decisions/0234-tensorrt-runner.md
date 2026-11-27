# ADR-0234 · Execute a metadata-bound TensorRT engine without Torch

A serving application can instantiate `TensorRTRunner` with engine bytes, matching metadata and a visible CUDA device index. Before inference it validates the digest, TensorRT version, ROIAlign plugin, recorded CUDA runtime when present, tensor signatures and engine profiles. The caller owns scheduling and serializes calls to a runner.

Inference accepts the declared input tensors and returns detections and counts. Each call owns its allocations and CUDA stream. The NumPy preprocessing helpers handle normalization, resizing and original-coordinate recovery. Unit cases with simulated SDK calls cover validation and cleanup. Actual latency, device memory and predictions require a live engine.

[Export command](../docs/commands/cy-export.md) · [Standalone runner](../src/clearml_yolo/adapters/export/runtime.py) · [NumPy preprocessing](../src/clearml_yolo/adapters/export/preprocessing.py) · [Runtime and geometry cases](../tests/test_detector_export.py)

See [export metadata](0235-export-metadata.md) and [optimization profiles](0236-optimization-profiles.md).
