# ADR-0231 · Export Faster R-CNN as a standard CPU FP32 ONNX graph

Graph export starts from a native checkpoint whose descriptor agrees with the selected Faster R-CNN preset and preprocessing contract. CY reconstructs the detector, strictly loads its weights and exports opset 17 in CPU FP32. The graph includes proposal and region-of-interest processing and freezes the confidence, NMS IoU and maximum detection count selected for export.

The operation emits `model.onnx` and a companion containing its digest, descriptor and inference policy. Engine precision and device selection occur at build time. Changing an embedded inference threshold therefore requires a new graph.

[Export command](../docs/commands/cy-export.md) · [ONNX graph export](../src/clearml_yolo/adapters/export/onnx.py) · [Graph and metadata assembly](../src/clearml_yolo/adapters/integrations/export_operations.py) · [Graph output and shape contracts](../tests/test_detector_export.py) · [CPU export admission](../tests/test_export.py)

See [checkpoint descriptors](0207-checkpoint-descriptor.md) and [export metadata](0235-export-metadata.md).
