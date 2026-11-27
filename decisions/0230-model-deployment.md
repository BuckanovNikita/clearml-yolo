# ADR-0230 · Export, build and verify a Faster R-CNN deployment

`cy-export` turns a Faster R-CNN checkpoint into a standard ONNX graph, builds a TensorRT engine for a target device, and verifies the engine against the source model. Each invocation selects one operation and owns one ClearML task. Bound artifacts and their metadata carry the inference contract across these three steps.

## Exporting the model and its inference policy

Graph export requires a native checkpoint whose descriptor agrees with the selected preset and preprocessing. CY reconstructs the detector, loads weights strictly and emits a CPU FP32 opset-17 graph that includes proposal and ROI processing. The graph fixes confidence, NMS IoU and maximum detections. Changing one of these requires another export.

The JSON sidecar binds the checkpoint descriptor, graph digest, inference policy and optimization profiles. Engine build adds the engine digest, precision, plugin requirements and runtime versions. Each consumer checks the identities it needs. The technical reference describes immutable sidecars. When a successful export or build reuses an explicit output directory, the writer can replace the sidecar at its fixed output name. Downstream validation still checks the input metadata. [Export contract](../DOCS.md#export) · [Documented discrepancy](https://linear.app/sip-ds-team/issue/SIP-353)

The task publishes the operation's artifacts and records `export_result` as provenance. No additional Output Model is registered. A verification failure can leave local evidence and an available quality report is published before a failed quality verdict is raised. [Command guide](../docs/commands/cy-export.md)

<details>
<summary>Sources and verification</summary>

- Run each detector export operation as its own task — [Export workflow](../src/clearml_yolo/application/use_cases/export.py) · [Operation admission](../src/clearml_yolo/core/export_requests.py) · [Inputs and publication ordering](../tests/test_export_workflow.py) · [Early artifact publication](../tests/test_early_export_publication.py)
- Export Faster R-CNN as a standard CPU FP32 ONNX graph — [ONNX graph export](../src/clearml_yolo/adapters/export/onnx.py) · [Graph and metadata assembly](../src/clearml_yolo/adapters/integrations/export_operations.py) · [Graph output and shape contracts](../tests/test_detector_export.py) · [CPU export admission](../tests/test_export.py)
- Bind graph, engine and inference policy with a sidecar — [Metadata schema](../src/clearml_yolo/core/export.py) · [Sidecar writer](../src/clearml_yolo/adapters/export/metadata.py)

</details>

## Building for a device and shape range

Build verifies the ONNX graph identity and compiles on a selected GPU at FP32 or FP16. It lowers ROIAlign to the registered version-two TensorRT plugin in the build representation and handles FP16 precision explicitly. Missing runtime requirements or unsupported settings fail the build. A serialized engine still needs quality verification.

Full frames and long strips have separate minimum, optimum and maximum NCHW profiles. Each requires three channels, a supported batch and spatial sides divisible by 32. The builder installs these profiles. Serving selects a profile covering the input and rejects shapes outside them. Expanding the range requires a compatible engine and verification over the expanded range.

<details>
<summary>Sources and verification</summary>

- Compile a TensorRT engine for an explicit GPU and precision — [Export command](../docs/commands/cy-export.md) · [Engine builder and plugin lowering](../src/clearml_yolo/adapters/export/build.py) · [FP16 graph policy](../src/clearml_yolo/adapters/export/precision.py) · [Builder and profile cases](../tests/test_detector_export.py) · [Explicit precision cases](../tests/test_export_precision.py)
- Bound the engine's input shapes with optimization profiles — [Declared profile shapes](../src/clearml_yolo/core/export.py) · [Runner checks](../src/clearml_yolo/adapters/export/runtime.py) · [Verification cases](../src/clearml_yolo/adapters/export/verification.py) · [Verification coverage cases](../tests/test_export_workflow.py)

</details>

## Verifying quality against the checkpoint

Verification freezes a labeled corpus from the requested split, including image hashes, and evaluates the native checkpoint and matching engine on the same cases. It checks preprocessing, profile endpoints, transitions and unsupported shapes. A usable reference requires observed detections and positive mAP.

The maximum mAP50–95 loss is 0.001 for FP32 and 0.005 for FP16. The engine must also produce at least one nonzero COCO metric among mAP, AP50, recall and per-class recall. An all-zero result fails even when the mAP loss is within tolerance. The report records the verdict and detection-matching diagnostics. Only an actual engine run establishes quality for those bytes and that hardware. [Quality gate](../src/clearml_yolo/core/export_quality.py)

<details>
<summary>Sources and verification</summary>

- Compare the exported engine against its source checkpoint — [Export command](../docs/commands/cy-export.md) · [Corpus and profile verification](../src/clearml_yolo/adapters/export/verification.py) · [Evaluator](../src/clearml_yolo/adapters/export/quality.py) · [Quality boundary cases](../tests/test_export_quality.py) · [Corpus and publication cases](../tests/test_export_workflow.py)

</details>

## Running the verified engine

`TensorRTRunner(engine_path, metadata, *, device=0)` takes a path to the serialized engine, a matching `ExportMetadata` object and an optional CUDA device index. Before inference it checks the engine digest, TensorRT version, ROIAlign plugin, recorded CUDA runtime when available, tensor signatures and profiles.

The caller serializes calls and owns scheduling. Each inference call owns its allocations and CUDA stream and returns detections and counts. NumPy helpers implement normalization, resizing and recovery of original-image coordinates without Torch. Simulated SDK cases cover validation and cleanup. Latency, memory use and prediction quality require the target engine and device. [Runner interface](../src/clearml_yolo/adapters/export/runtime.py)

<details>
<summary>Sources and verification</summary>

- Execute a metadata-bound TensorRT engine without Torch — [Export command](../docs/commands/cy-export.md) · [NumPy preprocessing](../src/clearml_yolo/adapters/export/preprocessing.py) · [Runtime and geometry cases](../tests/test_detector_export.py)

</details>
