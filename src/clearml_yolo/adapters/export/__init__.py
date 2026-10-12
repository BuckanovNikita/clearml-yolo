"""Optional detector export and portable TensorRT execution adapters.

Importing this package does not initialize Torch, TensorRT, CUDA or ClearML.
"""

from clearml_yolo.adapters.export.onnx import ONNXExportResult, export_onnx

__all__ = ["ONNXExportResult", "export_onnx"]
