# TensorRT SDK and plugin loading — 2026-11-16

Status: SDK import and required plugin registration passed in both isolated
environments. This extends the earlier [installation evidence](2026-11-16-export-prerequisites.md).
Engine compilation, GPU execution, profile coverage and numerical parity remain
deferred; no export ticket is accepted by this check.

The coordinator reviewed the exact proposed body against the maintained
`src/clearml_yolo/adapters/export/runtime.py` registry calls. A separate executor
ran it with each environment's explicit Python, CUDA hidden, one numerical thread,
isolated imports and a 30-second owned-process deadline. The body constructs no
builder, runtime, engine, model or execution context. It asserts TensorRT 10.13.0.35,
successful plugin initialization, the `ROIAlign_TRT:2` creator, and absence of
Torch and ClearML imports.

Both children exited 0 with the exact passed JSON and empty stderr: build in
0.925 seconds and standalone in 0.673 seconds. All child groups and supervisor exited.
The coordinator inspected the script and receipt independently of the executor.
No environment, dependency pin or product source changed. CUDA visibility does
not prove that native library initialization never contacts the driver.

Retained directory:
`.tmp/verification-gap-closure/export-environment-plan-20261116/sdk-probe-20261116T175458Z-1036362/`.

- `receipt.json`: `45fda1e8834036b25b44268b126c46c25080ed3eb0dfc2ee4153e7aca258198b`.
- `supervisor-exit.json`: `0db7f0d23f528ea353967908c46c101a07ab1a0980d15c5b55da5ff9aa0b1917`.
- Probe source in the parent directory, `sdk_plugin_probe.py`: `54ce15cff6c1bfb81f8f021be52b61570d52dcc0f7035ede1c64e8131e36a42d`.
- Product runtime source: `07ba671d26fa55fd63a9174c28bb47827564933989f43d7e7f67792f77080890`.

Setup's original proposal and receipt remain unchanged. Qualified producer
checkpoints and the frozen quality corpus are still required for real export
verification, under the user's free-VRAM constraint.
