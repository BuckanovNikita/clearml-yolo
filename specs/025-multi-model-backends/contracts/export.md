# Faster R-CNN export and standalone runtime contract

## Command

`cy-export` is a Hydra execution command with the existing ClearML, queue/autogpu,
bootstrap, replay, output ownership and failure contracts. Its default model selection is
`model=fasterrcnn/resnet50_fpn`; every Faster R-CNN preset is supported.

| Field | Contract |
| --- | --- |
| `export.operation` | `onnx`, `build`, `verify`; default `onnx` |
| `weights` | Required for ONNX export and native verification |
| `output_dir` | Optional explicit destination; otherwise normal invocation-owned output |
| `export.precision` | `fp32` for CPU ONNX; `fp32` or `fp16` for engine build/verification |
| `export.device` | Default `cpu` for ONNX export; GPU build/verification require GPU selection such as `0` or `-1` and reject CPU |
| `export.onnx` | Existing ONNX input required for `build`, with source metadata |
| `export.engine` | Existing serialized engine required for `verify`, with source metadata |
| `export.metadata` | Optional sidecar path; otherwise `<source-artifact>.json` |
| `export.workspace_gib` | Positive TensorRT builder workspace bound; default 4 |
| `export.split` | Fixed corpus split: `train`, `val` or `test`; default `test` |
| `ground_truth` | Fixed labeled corpus required for verification |

CPU-only ONNX generation has zero GPU demand and bypasses GPU discovery. Engine build
and GPU verification reserve one GPU using existing admission. All operations own one
task and publish the artifacts produced by that operation with source lineage; they do
not register another trained Output Model.
Executable settings remain under `export`; generated evidence is stored under `export_result`
and cannot overwrite replay inputs. Recorded evidence preserves empty lists and mappings,
including the ONNX plugin inventory, so it agrees with the published metadata/report.

| Operation | Published artifacts | Structured evidence |
| --- | --- | --- |
| `onnx` | `export_onnx`: `model.onnx`; `export_metadata`: `model.onnx.json` | `export_result` binds the source descriptor, graph hash, inference policy and runtime versions |
| `build` | `export_engine`: `model.engine`; `export_metadata`: `model.engine.json` | `export_result` binds source/graph/engine hashes, precision, profiles, runtime versions and plugins |
| `verify` | `export_verification`: `verification.json`; `export_corpus`: `corpus.json` | `export_result` records verification outcomes and corpus identity |

Each finalized graph, engine, metadata document and corpus manifest uploads as soon as it
is complete. The final verification report uploads only after all cases and corpus checks
finish; intermediate report writes remain local. A completed report whose quality gate fails
still uploads before the task fails. No intermediate artifact replacement occurs. Earlier
complete files remain available if a later producer fails, and upload rejection stops work.
The optional typed artifact-ready callback carries names and paths through the export port;
export adapters do not acquire ClearML SDK dependencies. Finalization still verifies uploads.

The build report consists of structured `export_result` and the engine metadata sidecar;
there is no separate build-report file or artifact. Verification accepts a corpus containing
only the selected split; ordinary training retains its required training/validation populations.

## Dynamic engine input and outputs

The engine uses dynamic NCHW batches and one common canvas per batch. Preserve RGB
normalization, aspect-preserving resize, padding, valid-image dimensions and box restoration
identically in native/exported paths. Metadata defines tensor names/types/layouts and all
pre/postprocessing parameters. DINO patch padding is explicit and is reversed correctly.

Dimensions below are width × height; each profile has batch min/opt/max **1/2/4**.

| Profile | Minimum | Optimum | Maximum |
| --- | --- | --- | --- |
| Full frames | 960×608 | 960×608 | 960×736 |
| Strips | 1536×128 | 1920×256 | 1920×256 |

Accept batches 1, 2, 3 and 4 within one complete profile; validate requested canvas/valid
sizes before execution. Reject cross-profile or out-of-profile shapes. Support profile
switches and dynamic spatial dimensions, not only endpoint-specific fixed graphs.

Proposal generation, ROI processing and NMS execute inside the engine. Outputs represent
per-image detection counts with boxes, class IDs and scores; padded output slots, if used,
are excluded by explicit counts. Empty detections are valid and must not become fake boxes.
Preserve numerical interpolation semantics for DINO positional features and lower rotary
operations explicitly. Start at ONNX opset 17; record any verified operator adjustments
and version every required plugin with source/build identity.

FP16 builds use a strongly typed graph. Eligible backbone weighted MatMul/Gemm products and
eligible 1×1 convolutions use Half-rounded operands, private Float matrix accumulation,
an immediate Half product cast and Float restoration for consumers. Biases and Gemm
alpha/beta operations remain Float after product rounding; transposes and broadcasting
are preserved. The private cast pattern permits actual Half multiplication with Float
accumulation rather than exposing the Float product to another consumer.

Eligible convolutions require direct FP32 rank-four 1×1 initializer weights, group one,
zero padding, `auto_pad=NOTSET`, dilation one and positive two-dimensional strides.
NCHW matrix multiplication and explicit stride slicing preserve dynamic batch/spatial
dimensions, including odd spatial sizes. Other convolutions remain Float. FPN and
RPN/ROI detection heads, including hidden projections, retain FP32 arithmetic, identified
by qualified parameter names independently of the backbone. Dynamic products and
non-weighted operations, including attention, geometry, ROIAlign and NMS, also remain
Float. TF32 is disabled. Lowering preserves external tensor names/types/shapes, original
initializer bytes and the source ONNX file. Conv/Gemm operations without direct FP32
initializer weights fail before graph mutation.

Combined QKV projections retain Float arithmetic to avoid amplified product-rounding
error through score multiplication and Softmax. Identify them independently of names
through the dynamic `MatMul(Softmax(...), V)` value path: squeeze axis zero, third output
of a `[1,1,1]` split on axis zero, transpose `[2,0,3,1,4]`, reshape and an optional Float
initializer bias addition after a direct Float `[C,3*C]` weighted MatMul. Split/axis
controls must be constant INT64 vectors. Bias must have shape `[3*C]`. Unsupported or
ambiguous value paths fail before mutation. A Softmax followed by a static weighted
product is not this attention boundary. Other eligible attention output projections
and MLP products continue using Half operands/products with Float accumulation.

## Bundle and standalone execution

The complete deployment bundle accumulates outputs from the ONNX, build and verification
operations: graph, engine, class/preprocessing metadata, dynamic profiles,
checkpoint/graph/engine hashes, target runtime/build metadata, required plugins and the
verification report. Each operation publishes only its own inventory above; retain the
earlier artifacts and sidecars when assembling the bundle. Engine loading validates
compatibility and complete metadata rather than guessing tensor semantics from shapes.

Produce a minimal standalone runner depending on TensorRT/CUDA bindings and ordinary
image/array utilities, with no Torch or ClearML requirement. It does not create a tracking
task. Neither native fallback nor host execution of detector proposals/ROI/NMS qualifies
as standalone engine support.

TensorRT **10.13.0** is the CUDA 11.8 compatibility target. Local acceptance uses its
supported newer-CUDA build in an isolated environment. Rebuild engines for the target
GPU/runtime; record local verification separately from unexecuted CUDA 11.8 deployment.
No binary portability is inferred from successful local execution.

## Verification gates

Before full preset expansion, prove real dynamic ResNet-50 and DINO export, engine build
and inference at rectangular sizes and batch four. Unsupported operators or materially
different preprocessing block that gate; do not reduce advertised scope silently.

For each of the six Faster R-CNN presets and both FP32/FP16:

1. Execute all four listed endpoint sizes at batches 1–4, interior profile shapes,
   repeated shape/profile changes, empty/crowded scenes and out-of-profile rejection.
2. Load the serialized engine in a fresh environment without Torch and run inference.
3. Bind identical checkpoint, input corpus, class mapping, preprocessing and evaluator.
   Use a fixed labeled test corpus with documented class/scene coverage and disjoint
   training, validation and test populations. Select the training recipe and checkpoint
   using validation, then freeze them before test evaluation. The test corpus must produce
   meaningful native reference predictions; test outcomes must not guide further training
   or tuning to obtain positive test quality. A small smoke corpus cannot establish quality
   for classes it does not cover.
4. Compare normalized inputs, available intermediate/raw tensors and class-aware
   one-to-one final detection matches. Report filtering/NMS effects separately from
   continuous numerical drift; confirm finite outputs and original-coordinate restoration.
5. Require absolute mAP50–95 loss at most **0.001 FP32** and **0.005 FP16**, and report
   per-class recall. These limits are quality gates, not universal raw-tensor tolerances.
6. Record actual latency/memory and execution environment without imposing an unspecified
   performance target. Unexecuted or failed checks cannot be reported as passing.
