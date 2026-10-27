# Research decisions

Date: 2026-10-26. Source inspection supplements the supplied design.

- Existing native training adapters share ModelConfig, PreparedDataset, output, scalar
  callback and BackendTrainResult. Preserve this API behind the worker boundary.
- Existing Linux process ownership supports PID birth validation and bounded cleanup;
  reuse it for worker supervision rather than signal unrelated workloads.
- Installed YOLO auto optimizer resolves AdamW or MuSGD. Its single-GPU OOM fallback
  can halve batch; probes must verify actual candidate batch and optimizer updates.
- Prepared dataset manifests contain class names and per-image box counts, enabling
  compatibility checks after preparation without rereading image tensors.
- Native DEIM setup can swallow distributed initialization errors. Initialize and
  verify the group before model/loaders. Lightning uses an external distributed launch
  to avoid relaunching the public CY command.
- Hydra automatically matches same-named ConfigStore entries and exported files.
  Use distinct schema names and explicit YAML defaults; no warning suppression.
- Full native multi-GPU acceptance is unavailable with the currently visible single
  GPU. Retain this as a gate, and execute available single-GPU/CPU evidence separately.
