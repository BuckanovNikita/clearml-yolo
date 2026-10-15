# TensorRT deployment contract

This guide describes the implemented interfaces and required deployment checks;
commands below are not execution evidence.
The [export contract](../specs/025-multi-model-backends/contracts/export.md) and
[validation guide](../specs/025-multi-model-backends/quickstart.md#faster-r-cnn-export-acceptance)
define acceptance for all six Faster R-CNN presets and both precisions.

Local results and any outstanding preset/precision gates are recorded in the
[dated verification ledger](../specs/025-multi-model-backends/verification.md).
CUDA 11.8 deployment has **not** been validated; local execution does not establish
compatibility with that target.

## Export, build and verify

Use a Faster R-CNN checkpoint carrying its validated descriptor and class vocabulary.
The application recreates the selected architecture without downloading pretrained assets
and loads the checkpoint state strictly. Confidence, class NMS IoU and maximum detections
come from `model.predict` and are baked into the graph; change them by exporting again.

ONNX generation currently requires `export.device=cpu export.precision=fp32`. It copies
the source model before adapting inference and does not alter that model. Engine build
and verification are separate GPU operations with their normal application admission.
The standalone library caller supplies scheduling and device selection itself.

These command forms match the [feature quickstart](../specs/025-multi-model-backends/quickstart.md):

```bash
uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn weights=./acceptance/best.pt \
  export.operation=onnx export.device=cpu output_dir=./acceptance/onnx \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-onnx \
  'clearml.tags=[feature025,export-acceptance]'

uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn export.operation=build \
  export.onnx=./acceptance/onnx/model.onnx export.device=0 export.precision=fp32 \
  output_dir=./acceptance/engine-fp32 \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-build \
  'clearml.tags=[feature025,export-acceptance]'

uv run --frozen --no-sync cy-export model=fasterrcnn/resnet50_fpn export.operation=verify \
  weights=./acceptance/best.pt export.engine=./acceptance/engine-fp32/model.engine \
  ground_truth=./acceptance/quality-truth.csv export.device=0 export.precision=fp32 \
  output_dir=./acceptance/verify-fp32 \
  clearml.project_name=multi-model-acceptance clearml.task_name=export-verify \
  'clearml.tags=[feature025,export-acceptance]'
```

Repeat build and verification with `export.precision=fp16` and a separate destination.
FP16 controls engine optimization; external image and detection tensors remain float32.
FP16 builds use explicit tensor types. Eligible backbone linear products and 1×1
convolutions round operands to FP16, accumulate their matrix product in FP32, round the
product to FP16, then restore FP32 for consumers. Each private FP32 matrix product has
an immediate FP16 result cast, allowing TensorRT to fuse the operand casts into Half
multiplication with Float accumulation. Bias addition and Gemm coefficient scaling
occur afterward in FP32. Gemm transposes and bias broadcasting are preserved.

Eligible convolutions have group one, no padding, dilation one and direct FP32 1×1
initializer weights. They become NCHW matrix products with explicit spatial slicing for
strides. Other convolutions, feature-pyramid operations and RPN/ROI detection heads,
including their hidden projections, remain FP32. Dynamic attention/interpolation products,
normalization, softmax, box geometry, ROIAlign and NMS also remain FP32. Strong typing
preserves these arithmetic boundaries; TF32 is disabled. Global FP16 optimization and
weak per-layer precision preferences are not used.

Combined attention QKV projections also remain FP32: rounding their products can amplify
through score multiplication and softmax. Selection follows the exported value branch
from `MatMul(Softmax(...), V)` through squeeze, the third QKV split, transpose and reshape
to the weighted projection, with an optional Float bias. It does not depend on backbone,
node or parameter names. Unsupported layouts at this boundary fail before conversion.
Other eligible attention output projections and MLP products retain mixed precision.
The conversion happens in memory and preserves the source ONNX bytes and external tensor
contracts. Conv/Gemm operations without direct FP32 initializer weights fail explicitly.
`export.workspace_gib` controls builder workspace and defaults to 4 GiB. It is neither
an inference memory limit nor a promise that every backbone fits that workspace.
The verified Swin recipe uses `export.workspace_gib=16`; its original 4 GiB build failed.

Keep `model.onnx` beside `model.onnx.json`, and `model.engine` beside `model.engine.json`.
The application discovers each sidecar by appending `.json` to the input artifact name;
`export.metadata` can select an explicit metadata path. Build checks the ONNX hash.
Verification binds the native checkpoint descriptor to the engine's source descriptor.
Sidecars contain the source checkpoint hash, vocabulary, normalization, inference policy,
profiles, opset, graph/engine hashes, precision, runtime versions and plugin identities.

## Dynamic tensors and profiles

Every batch uses one common RGB canvas. Tensor dimensions below are **N,C,H,W**;
canvas names in the validation contract use width × height.

| Profile | Minimum | Optimum | Maximum |
| --- | --- | --- | --- |
| Full frames | `(1,3,608,960)` | `(2,3,608,960)` | `(4,3,736,960)` |
| Strips | `(1,3,128,1536)` | `(2,3,256,1920)` | `(4,3,256,1920)` |

Batches 1, 2, 3 and 4 and interior canvas sizes are accepted when the entire shape fits
one profile and H/W are divisible by 32. For example, `(3,3,192,1728)` fits the strip
profile. `(1,3,736,1920)` spans the two profiles and is rejected. Repeated shape/profile
transitions require real acceptance execution; endpoint declarations alone do not prove
that a traced backbone remains dynamic.

| Tensor | Type and layout | Meaning |
| --- | --- | --- |
| `images` | float32 `[B,3,H,W]` | Normalized, padded RGB canvases |
| `image_sizes` | int64 `[B,2]` | Valid resized height/width before canvas padding |
| `detections` | float32 `[B,max_det,6]` | `x1,y1,x2,y2,confidence,native_label` |
| `counts` | int64 `[B]` | Valid leading detection rows for each image |

Inside the engine, labels are integer foreground IDs 1 through the vocabulary size.
`postprocess` subtracts one to produce zero-based vocabulary IDs. Rows after `counts`
are all zero and must be excluded. Zero detections are valid. The runner validates finite
values, counts, confidence/label ranges, ordered coordinates, valid-image bounds and
padding; detector proposal filtering, ROIAlign, decoding and NMS execute in the engine.

Portable preprocessing accepts RGB uint8 HWC arrays. It divides by 255, applies the
metadata's channel mean/std **before** bilinear resize (`align_corners=False`, no
antialiasing), fits the aspect ratio into the canvas, and pads the right/bottom with zero
in normalized space. Valid dimensions use the native rounding rule. Coordinate restoration
uses separate original/resized width and height ratios, preserving native float32
rounding (including a possible one-ULP boundary overshoot after restoration). The strict
valid-image bounds check applies before restoration. DINOv2 patch14 padding and
antialiased bicubic positional interpolation are handled in its export adapter; source
interpolation is not replaced with a different resize kernel to satisfy TensorRT.

## Standalone environment and library API

The inference library needs Python `>=3.12.13,<3.14`, the project wheel installed with `--no-deps`,
NumPy, Pydantic 2, matching TensorRT 10.13.0 bindings/libraries and a compatible CUDA
runtime library (`libcudart`). CUDA access uses `ctypes`; Torch, Torchvision, timm, ONNX,
ClearML and cuda-python are not standalone inference dependencies. Image decoding can
use a separately installed utility such as Pillow, or the caller can supply RGB arrays.
Select TensorRT bindings that support the chosen Python minor version; the package's
Python compatibility range does not establish vendor wheel availability or validate
a particular driver/runtime combination.

For a CUDA 12 deployment, a preparation command shape is shown below. Replace `VERSION`
with the built wheel version and install the appropriate NVIDIA CUDA runtime library.
Use the vendor distribution matching the CUDA 11.8 target when preparing that target;
this CUDA 12 package example does not validate CUDA 11.8 deployment.

```bash
python -m pip install --no-deps ./dist/clearml_yolo-VERSION-py3-none-any.whl
python -m pip install numpy 'pydantic>=2,<3' 'tensorrt-cu12==10.13.0.35'
```

Importing the following library modules does not import Torch, TensorRT or ClearML and
does not create a CUDA context. Constructing `TensorRTRunner` initializes TensorRT/CUDA;
select an admitted device before that point. Its `device` is a nonnegative index within
`CUDA_VISIBLE_DEVICES`, and the runtime calls `cudaSetDevice` explicitly.

```python
from pathlib import Path

import numpy as np

from clearml_yolo.adapters.export.metadata import read_metadata
from clearml_yolo.adapters.export.preprocessing import postprocess, preprocess
from clearml_yolo.adapters.export.runtime import TensorRTRunner

metadata = read_metadata(Path("bundle/model.engine.json"))
rgb = np.load("image-rgb.npy", allow_pickle=False)  # uint8 RGB HWC
images, sizes = preprocess(
    [rgb],
    (608, 960),
    mean=metadata.descriptor.preprocessing.mean,
    std=metadata.descriptor.preprocessing.std,
)
runner = TensorRTRunner(Path("bundle/model.engine"), metadata, device=0)
detections, counts = runner(images, sizes)
results = postprocess(
    detections,
    counts,
    [rgb.shape[:2]],
    sizes,
    class_count=len(metadata.descriptor.class_names),
)
```

The standalone runner creates no tracking task and performs no native model fallback.
Use one runner serially; its execution context is not intended for concurrent calls.
`cy-export verify` additionally needs the native model and evaluation dependencies to
compare against the labeled corpus, so it is a separate acceptance workflow.

The execution API is:

- `export_onnx(model, destination, sample_shape=(1,3,608,960))` returns `ONNXExportResult`.
- `build_engine(onnx_path, engine_path, precision="fp32", device=0,
  workspace_gib=4, profiles=DEFAULT_PROFILES)` uses keyword-only build controls and returns
  `EngineBuildResult` with engine hash, runtime versions and required plugins.
- `TensorRTRunner(engine_path, metadata, device=0)` requires metadata; the device is
  keyword-only. Calling it with normalized images and valid sizes returns detections/counts.
- `read_metadata`, `write_metadata` and `sha256` provide portable sidecar/hash handling;
  `OptimizationProfile`, `InferencePolicy` and `ExportMetadata` live in the scientific core.

## Runtime binding and rebuilding

The runner verifies the engine bytes against metadata **before** SDK loading or
deserialization, requires the exact recorded TensorRT 10.13.0 build, checks the recorded
CUDA runtime version when present, and validates engine tensor names/types/directions and
all optimization profiles. It requires the registered `ROIAlign_TRT` plugin version `2`.
Build lowers standard ONNX RoiAlign to that TensorRT plugin in memory, leaving the
portable ONNX file and its graph hash unchanged. Changing an SDK/plugin requires a new
build and new acceptance evidence.

Rebuild engines for the deployment GPU and runtime. A successful build on one GPU/CUDA
combination establishes no binary portability to another. TensorRT deserialization can
reject incompatible plans even when metadata is valid. Preserve the original graph,
checkpoint descriptor and hash identities; do not rewrite sidecars to bypass a mismatch.
See the [research](../specs/025-multi-model-backends/research.md#tensorrt-compatibility-and-parity)
for the official NVIDIA release-notes source and the distinction between the CUDA 11.8
target and newer-CUDA local execution.

## Acceptance and reported measurements

For every preset/precision, freeze the checkpoint hash, labeled corpus membership/image
hashes, preprocessing, vocabulary, inference policy and evaluator. Require meaningful
native detections, all shape/batch/profile-transition cases, empty/crowded inputs, rejection
cases and fresh standalone execution without Torch or ClearML. Numerical agreement and
quality are separate: class-aware one-to-one matches, score/box drift and NMS/filtering
changes describe output agreement; labeled-corpus mAP and per-class recall describe quality.

The absolute mAP50–95 loss limits are **0.001 FP32** and **0.005 FP16**. They are not
universal raw-tensor tolerances, and close boxes on an unlabeled image cannot establish
those quality gates. Report unexecuted gates as pending and failed gates as failed.

`runner.last_buffer_bytes` is the sum of successful I/O `cudaMalloc` request sizes in the
most recent call, including successful allocations before a failed call. It excludes
weights, context memory, allocator overhead and other processes. `runner.engine_context_bytes`
is TensorRT's `device_memory_size_v2`, the required execution-context device memory across
configured profiles and the engine's weight streaming budget. Neither value is total or
peak GPU memory. Native `torch.cuda.max_memory_allocated` measures the Torch allocator
separately and cannot measure the standalone runner's complete device usage. Record latency
scope, warmup policy and these memory meanings alongside measurements.

## Cross-contract integration

`cy-export` retains its executable `export` settings and stores generated evidence under
`export_result`, ignored during replay. It publishes operation-specific ONNX/engine,
metadata and verification artifacts without registering another trained model. CPU ONNX
has zero GPU demand; build/verify admit one device. The standalone runner validates hashes,
runtime/plugins, profiles, tensor semantics and foreground classes. Numerical diagnostics
and labeled-corpus mAP gates are separate; CUDA 11.8 target execution requires its own
dated evidence and cannot be inferred from local newer-CUDA success.
