# ADR-0232 · Compile a TensorRT engine for an explicit GPU and precision

The build operation reads a standard ONNX graph and its metadata, verifies graph identity, and compiles an engine on one selected GPU using the declared shape profiles. CY lowers ROIAlign to the registered version-two TensorRT plugin in the build representation. FP16 uses explicit precision handling for the graph. Unsupported settings or missing runtime requirements fail the build.

The output includes `model.engine` and metadata binding engine bytes, precision, plugins and runtime versions. Building an engine establishes serialization. Quality on labeled data is assessed by the separate verification operation.

[Export command](../docs/commands/cy-export.md) · [Engine builder and plugin lowering](../src/clearml_yolo/adapters/export/build.py) · [FP16 graph policy](../src/clearml_yolo/adapters/export/precision.py) · [Builder and profile cases](../tests/test_detector_export.py) · [Explicit precision cases](../tests/test_export_precision.py)

See [optimization profiles](0236-optimization-profiles.md) and [verification](0233-export-verification.md).
