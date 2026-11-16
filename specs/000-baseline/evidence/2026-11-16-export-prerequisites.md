# Export prerequisite environments — 2026-11-16

Status: isolated installation and metadata/provider checks passed. TensorRT loading,
plugin registration, GPU execution, exports and numerical parity remain deferred.
This does not accept export tickets 74–85; qualified producer checkpoints from
tickets 68–73 remain pending. The [paired JSON](2026-11-16-export-prerequisites.json)
binds every retained setup/check receipt by SHA-256.

The approved plan and installed source snapshot are
`5c0ece16a73ecc9ce279b564b7d69471c69007fa`; the root checkout during setup was
`ba56e2f2751954fb9c65799817d22b9e51b36b89`. Source/configuration and approved local
archive hashes matched before execution. Python is 3.12.13 and uv is 0.11.32.
No source/dependency pins were changed and root, managed and historical paired
environments were not installation targets. Root distribution metadata was checked
unchanged afterward.

## Installed and checked

Both environments belong to
`.tmp/verification-gap-closure/export-environment-plan-20261116/`:

- `build-env`: 289 exact distributions, approved locked CY dependencies plus pinned
  TensorRT/CUDA prerequisites and the two frontend build helpers; `uv pip check`
  and the exact package/source/provider check passed.
- `standalone-env`: 11 exact distributions: CY, the six approved NumPy/Pydantic
  support packages, and four TensorRT/CUDA packages. Torch, Torchvision, ClearML,
  timm, ONNX/ORT, FiftyOne and cv2 cannot resolve. Both OpenCV distributions are
  absent. This intentionally minimal deployment subset uses exact inventory checks
  rather than claiming the full CY training dependency graph is installed.

TensorRT frontend, bindings and libraries are each `10.13.0.35`; CUDA 12 runtime is
`12.8.90`. Build helpers are pip 25.2 and wheel 0.48.0. All six vendor/helper
downloads passed the exact recorded size and SHA-256 checks. The NVIDIA library
wheel hash is `6dc691e6b0a2298946327e1cca3c829c23586e498c4c01ef74b5fd41f9042cb1`.
The vendor frontend wheel was built locally with its internal installer disabled;
its hash is `efff59e05015a90a9f9e706e7d055ca432e9d1afe9a2c93a7fb16ccbf4f52a51`.
No CY release distribution was produced.

Ticket 100's provider check initially failed after locked sync. The one reviewed
offline, no-dependency reinstall of exact `opencv-python==5.0.0.93` then passed:
actual cv2 5.0.0 and all 15 Python/native-library execution files match root.
Before/after receipts remain intact. This reproduces root's hybrid execution files,
including its retained gapi module; it does not resolve the overlapping dependency
graph or establish historical training equivalence.

## Ownership and retained resources

Setup ran at nice 19/idle I/O priority from 17:44:13 to 17:48:38 UTC, exit 0 in
264.83 seconds. Managed session 89712 owned supervisor PID 817482 and child group
817487. Both PIDs and all members of the owned process group were absent afterward.
The supervisor enforced an 1800-second timeout and retained commands, PID/start,
stdout/stderr and final status. There was no automatic retry.

The private cache and copy installation mode preserve shared inputs. Logical sizes
are 12,123,369,517 bytes for build, 4,757,960,694 for standalone, 12,613,771,279 for
private cache and 3,119,680,370 for vendor downloads. These reusable prerequisites,
the source snapshot and frontend wheel remain retained. Filesystem free space
decreased from 741,486,628,864 to 690,662,100,992 bytes; concurrent activity prevents
attributing that whole delta to this task. Cleanup must target only task-owned
generated paths, preserving receipts and external symlink targets.

Key receipt hashes:

- Installation: `1b2ef555faec004ea8d40bbdd1dedd33803822dbd2115a50993628ad9e4e6195`.
- Build metadata: `c15e07d4d489772dc5e9bcd8ce2e88c9bd73bd62fe3a67f94a7e58b20b635d7d`.
- Minimal metadata: `e858b4e326cac7818c2c431a2e6a58e612a49e70a6515026d1056733eb37087a`.

## Proposed next bounded check — not executed

After coordinator review, use each environment's explicit interpreter in a fresh
owned subprocess with CUDA hidden, one numerical thread and a 30-second timeout.
Retain PID/start, command, stdout/stderr, exit and cleanup under the task directory.
The proposed Python body below follows the maintained registry calls in
`adapters/export/runtime.py`; it does not construct a builder, runtime, engine,
model or execution context.

```python
import importlib.metadata
import json
import os
import sys

assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
assert importlib.metadata.version("tensorrt-cu12") == "10.13.0.35"
import tensorrt as trt

assert trt.__version__ == "10.13.0.35"
logger = trt.Logger(trt.Logger.ERROR)
assert trt.init_libnvinfer_plugins(logger, "")
creator = trt.get_plugin_registry().get_creator("ROIAlign_TRT", "2", "")
assert creator is not None
assert "torch" not in sys.modules and "clearml" not in sys.modules
print(json.dumps({"version": trt.__version__, "plugin": "ROIAlign_TRT:2", "status": "passed"}))
```

Invoke with `env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1`, nice 19/idle I/O, explicit `build-env/bin/python -I -B` and then
`standalone-env/bin/python -I -B`. A supervisor must terminate and reap the owned
process group on timeout/interruption. CUDA visibility is a restriction, not proof
that vendor library initialization never touches the driver. A failed import or
registry check is a prerequisite failure; do not change versions or search another
plugin automatically. No such import has been performed yet.

Even a future successful registry check will establish only SDK loading and plugin
availability. The maintained [deployment contract](../../../docs/tensorrt-deployment.md)
still requires qualified checkpoints, the frozen quality corpus, engine/profile
execution and numerical parity, with the user's whole-device reserve maintained.
