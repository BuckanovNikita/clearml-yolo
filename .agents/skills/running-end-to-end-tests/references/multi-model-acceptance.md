# Detector and export verification

Paths start at the repository root. Select affected matrix rows in
`docs/multi-model-backends.md` and `docs/tensorrt-deployment.md`. These contracts own
presets, numerical tolerances, execution cases and target compatibility.

- For native detector changes, exercise affected advertised presets with short real
  training, pretrained initialization, best selection, copied/downloaded checkpoint
  reload and prediction/validation. Use the `tests/test_detector_*.py` and backend
  product regressions for local behavior, then record actual native execution and
  publication. Random-weight smoke proves execution only.
- For cross-family changes, run direct and queued single-GPU comparisons on identical
  images with frozen thresholds. Inspect descriptor/source identity and effective
  preprocessing using `tests/test_comparison_reinfer.py` and actual downloaded results;
  preserve cancellation and owned-process cleanup.
- For Faster R-CNN export changes, use `tests/test_export_*.py` and the concrete
  `cy-export`/verification commands in the deployment guide. Build and execute actual
  ONNX/TensorRT outputs for its required cases, including a fresh runtime without Torch
  or ClearML. Freeze corpus/checkpoint/evaluator identity; report quality, numerical
  comparisons, latency and memory separately. A newer-CUDA local result does not prove
  an older target, and a quality report does not prove standalone execution.

Temporary unavailable supported dependencies or hardware defer the corresponding
claim. Record the exact unexecuted matrix rows instead of claiming a whole backend.
