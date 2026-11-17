# Export

Export turns a trained Faster R-CNN checkpoint into a deployable TensorRT engine and
checks that the engine still detects as well as the native model. `cy-export` runs one of
three separate operations per invocation: `onnx` writes a portable ONNX graph on the CPU,
`build` compiles that graph into a TensorRT engine for one GPU at FP32 or FP16, and
`verify` compares the engine with the native checkpoint on a fixed labelled corpus. Each
artifact carries a metadata sidecar that binds it to its checkpoint, classes,
preprocessing and inference settings, and a NumPy/TensorRT runner executes engines without
Torch or ClearML.

## Behavior

### Operations

```bash
cy-export model=fasterrcnn/resnet50_fpn export.operation=onnx weights=./best.pth \
  output_dir=./onnx
cy-export model=fasterrcnn/resnet50_fpn export.operation=build \
  export.onnx=./onnx/model.onnx export.device=0 export.precision=fp16 output_dir=./engine-fp16
cy-export model=fasterrcnn/resnet50_fpn export.operation=verify weights=./best.pth \
  export.engine=./engine-fp16/model.engine ground_truth=./quality-truth.csv \
  export.device=0 export.precision=fp16 output_dir=./verify-fp16
```

- **`onnx`** needs `weights` with a validated checkpoint descriptor. It rebuilds the
  selected architecture without downloading pretrained assets, loads the checkpoint
  strictly and writes `model.onnx` and `model.onnx.json` from a copy of the model. The
  confidence threshold, class NMS IoU and maximum detections come from `model.predict`
  (`conf`, `iou`, `max_det`) and are baked into the graph; change them by exporting
  again. Proposal filtering, ROIAlign, box decoding and NMS run inside the graph.
- **`build`** needs `export.onnx`. It checks the graph hash against the metadata, lowers
  standard RoiAlign to the TensorRT `ROIAlign_TRT` plugin version 2 in memory (the ONNX
  file and its hash are unchanged) and writes `model.engine` and `model.engine.json`.
- **`verify`** needs `export.engine`, `weights` and labelled `ground_truth`. The
  checkpoint descriptor must equal the engine's source descriptor, and the requested
  precision must equal the engine's. It writes `corpus.json` and `verification.json`.
- A sidecar is found by appending `.json` to the input artifact name; `export.metadata`
  selects another path. Sidecars record the source checkpoint descriptor and hash,
  vocabulary, normalization, inference policy, profiles, opset 17, graph and engine
  hashes, precision, runtime versions and plugins. Keep each sidecar beside its artifact.

### Precision

FP16 controls engine optimization only; external image and detection tensors stay
float32. FP16 engines are strongly typed with TF32 disabled: eligible backbone linear
products and 1×1 convolutions use FP16 operands with FP32 accumulation, while
convolutions with other shapes, the feature pyramid, the RPN and ROI heads, combined
attention QKV projections, normalization, softmax, box geometry, ROIAlign and NMS stay
FP32. A Conv or Gemm without direct FP32 initializer weights, or an unsupported
attention layout, fails before conversion. Global FP16 mode and per-layer precision
hints are not used.

### Dynamic shapes and tensors

Every batch uses one common RGB canvas. Shapes are N,C,H,W:

| Profile | Minimum | Optimum | Maximum |
| --- | --- | --- | --- |
| Full frames | `(1,3,608,960)` | `(2,3,608,960)` | `(4,3,736,960)` |
| Strips | `(1,3,128,1536)` | `(2,3,256,1920)` | `(4,3,256,1920)` |

A batch of 1–4 with any interior canvas is accepted when the whole shape fits one
profile and H and W are divisible by 32; `(3,3,192,1728)` fits the strip profile,
`(1,3,736,1920)` spans both and is rejected.

| Tensor | Type and layout | Meaning |
| --- | --- | --- |
| `images` | float32 `[B,3,H,W]` | Normalized, padded RGB canvases |
| `image_sizes` | int64 `[B,2]` | Valid resized height and width before padding |
| `detections` | float32 `[B,max_det,6]` | `x1,y1,x2,y2,confidence,native_label` |
| `counts` | int64 `[B]` | Valid leading detection rows per image |

Engine labels are foreground IDs 1 to the vocabulary size; `postprocess` subtracts one
to give zero-based class IDs. Rows after `counts` are zero and are ignored; zero
detections are valid. The runner validates finite values, counts, confidence and label
ranges, ordered coordinates, valid-image bounds and padding.

Preprocessing takes RGB uint8 HWC arrays: it divides by 255, applies the metadata's
channel mean and std before a bilinear resize (`align_corners=False`, no antialiasing),
fits the aspect ratio into the canvas and pads right and bottom with zero in normalized
space. Coordinates are restored with separate width and height ratios in float32, so a
one-ULP overshoot at the image edge is possible after restoration.

### Standalone runner

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

- Importing these modules loads neither Torch, TensorRT nor ClearML and creates no CUDA
  context. Constructing `TensorRTRunner` initializes TensorRT and CUDA; `device` is a
  non-negative index within `CUDA_VISIBLE_DEVICES`. Use one runner from one thread at a
  time.
- Before deserializing, the runner checks the engine SHA-256 against the metadata,
  requires the exact recorded TensorRT 10.13.0 build and the `ROIAlign_TRT:2` plugin,
  checks the recorded CUDA runtime version, and validates tensor names, types,
  directions and every optimization profile. It creates no ClearML task and never falls
  back to the native model.
- Library entry points: `export_onnx`, `build_engine`, `read_metadata`,
  `write_metadata`, `sha256`; the metadata models live in `clearml_yolo.core.export`.
  `runner.last_buffer_bytes` and `runner.engine_context_bytes` report I/O allocations
  and execution-context memory, not total or peak GPU memory.

### Verification and quality gates

`verify` freezes the corpus (ground-truth bytes and image hashes in `corpus.json`) and
runs the FP32 native model (TF32 disabled) and the engine on identical bytes for every
profile endpoint at batches 1–4, interior canvases and repeated profile switches. For
each case it records native and engine COCO mAP, mAP50, recall and per-class recall,
class-aware one-to-one detection agreement at IoU 0.99, preprocessing error, latency and
memory scopes. Verification passes only when every case keeps the absolute mAP50–95 loss
within **0.001 (FP32)** or **0.005 (FP16)** with a meaningful native baseline, every
preprocessing comparison is within tolerance, out-of-profile inputs are rejected and the
corpus is unchanged. Detection agreement is evidence, not a gate.

### Publication

`cy-export` uses one ClearML task (`<task_name>/export` when run standalone) and uploads
each file as soon as it is ready: `export_onnx`, `export_engine`, `export_metadata`,
`export_corpus` and `export_verification`. It registers no Output Model. The checkpoint
identity is recorded under `source_model` and the operation's evidence under
`export_result` in the `run` configuration; replay ignores `export_result`.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `export.operation` | `onnx` | `onnx`, `build` or `verify` |
| `export.device` | `cpu` | `onnx` requires `cpu`; `build`/`verify` need exactly one GPU (`0`, `cuda:1`; `-1` and `cuda` mean GPU 0) |
| `export.precision` | `fp32` | `onnx` requires `fp32`; `fp16` is chosen at build and must match at verify |
| `export.onnx` | `null` | Graph for `build` |
| `export.engine` | `null` | Engine for `verify` |
| `export.metadata` | `null` | Sidecar path; `null` uses the artifact name plus `.json` |
| `export.workspace_gib` | `4` | Positive TensorRT builder workspace in GiB, not an inference memory limit |
| `export.split` | `test` | Labelled split (`train`, `val`, `test`) used as the verification corpus |

`weights`, `ground_truth` and `output_dir` are command inputs; `model` must select a
Faster R-CNN preset ([detector families](detector-families.md)), and the exported
example configuration uses `fasterrcnn/resnet50_fpn`. Large backbones may
need a bigger `export.workspace_gib`.

## Failure behavior

- Missing operation inputs fail before any export work starts. `onnx` with a GPU
  or `fp16`, `build`/`verify` without exactly one GPU, and any non-Faster R-CNN model
  are rejected at validation.
- A changed ONNX graph, a preset or descriptor that disagrees with the metadata, a
  precision mismatch, an engine hash mismatch, a different TensorRT version, a missing
  plugin or an incompatible plan fails before inference. Do not rewrite sidecars to
  bypass a mismatch; rebuild instead.
- Invalid boxes in the quality corpus fail verification, as does a selected split with
  no images or no labelled object at all; unlabelled background images are allowed
  alongside labelled ones. A corpus file changed during verification fails.
- A failed quality gate uploads the verification report and corpus manifest, then fails
  the command with `Export verification failed; inspect the retained verification
  report`.

## Limits

- Only Faster R-CNN presets export.
- Engines are tied to the GPU, TensorRT build and CUDA runtime that built them; rebuild
  for each deployment target. A successful build establishes no portability, and any
  SDK or plugin change needs a new build and new verification.
- An engine works only on the CUDA runtime it was built and verified against;
  verification on one CUDA version does not establish another (for example a CUDA 11.8
  target).
- Raw pre-NMS outputs are not exposed, so verification compares final detections only.
- The standalone runner needs Python `>=3.12.13,<3.14`, the project installed with
  `--no-deps`, NumPy, Pydantic 2, Loguru, TensorRT 10.13.0 bindings and libraries, and a
  compatible CUDA runtime library (`libcudart`). TensorRT is provisioned separately and
  is not a project dependency; `cy-export verify` additionally needs the native model and
  evaluation dependencies. Torch, Torchvision, timm, ONNX, ClearML and cuda-python are
  not runner dependencies; decode images yourself (for example with Pillow) or pass RGB
  arrays. For a CUDA 12 target, from the project source checkout:

  ```bash
  python -m pip install --no-deps .
  python -m pip install numpy 'pydantic>=2,<3' 'loguru>=0.7.0' 'tensorrt-cu12==10.13.0.35'
  ```

  plus the matching NVIDIA CUDA runtime library. Choose TensorRT bindings that support
  your Python minor version; for a CUDA 11.8 target use that target's vendor
  distribution.
- The default workspace does not guarantee every backbone builds.

## Code and tests

- [`application/use_cases/export.py`](../../src/clearml_yolo/application/use_cases/export.py) — task, uploads and evidence
- [`adapters/integrations/export_operations.py`](../../src/clearml_yolo/adapters/integrations/export_operations.py) — operation dispatch and sidecar binding
- [`core/export_requests.py`](../../src/clearml_yolo/core/export_requests.py) — options and input rules
- [`core/export.py`](../../src/clearml_yolo/core/export.py) — metadata, profiles, inference policy
- [`core/export_quality.py`](../../src/clearml_yolo/core/export_quality.py) — agreement and quality gate
- [`adapters/export/`](../../src/clearml_yolo/adapters/export/) — ONNX, build, precision, runtime, preprocessing, verification
- Tests: [`test_export.py`](../../tests/test_export.py),
  [`test_export_workflow.py`](../../tests/test_export_workflow.py),
  [`test_export_precision.py`](../../tests/test_export_precision.py),
  [`test_export_attention_precision.py`](../../tests/test_export_attention_precision.py),
  [`test_export_quality.py`](../../tests/test_export_quality.py),
  [`test_detector_export.py`](../../tests/test_detector_export.py)
- TensorRT builds and quality gates on a real GPU are established only by GPU runs; the
  unit suite mocks the TensorRT runtime.
