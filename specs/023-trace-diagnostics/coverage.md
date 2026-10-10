# TRACE coverage inventory

Implementation inventory and review scope, 2026-10-10. Read this alongside the
[specification](spec.md); unit tests establish instrumentation and unchanged behavior,
while dated native evidence separately establishes actual execution.

| Boundary | Instrumentation owner and operation families | Acceptance evidence |
| --- | --- | --- |
| All ten commands | entrypoints/hydra/common.py launch/execute and local config_tree/dedup mains; command.*, configuration.*, filesystem.initialize | test_trace_subprocess all command helps; test_direct_execution; native pipeline |
| Workflows and composition | application use cases and evaluation via ExecutionResources.trace_operation; workflow.*, evaluation.split, comparison.bootstrap, publication.* | application-port/entrypoint/architecture tests; current workflow suite |
| GPU waiting | runtime GPU visibility subprocess, NVML snapshot, complete wait and selected logical devices | test_trace_runtime; existing GPU wait/resources tests |
| Native setup/cleanup | integrations native imports/setup/restoration, separate GC/synchronize/cache release and temporary-directory cleanup | test_trace_runtime; real CPU/GPU pipelines |
| Training and DDP | native train/model load/finalize; relay start/consumer/callback/replay/join/cleanup | test_trace_runtime; native CPU DDP regression suite; native single GPU |
| Cache/conversion/export | storage source read/hash, lock acquire separately from held lifetime, validate/hit/miss/publish, dataset validation/export/materialize/NDJSON/YAML/ZIP | test_trace_storage; existing cache and dataset tests |
| Files and snapshots | storage filesystem init, text/CSV ports, checkpoint hash/identity, native archive, publication data, aggregate dedup | test_trace_storage; existing filesystem/identity/dedup tests |
| Prediction/reinference | YOLO checkpoint/model/vocabulary loads, full lazy inference stream, cache read/hit/miss/write | test_trace_compute; existing inference/reinfer tests; native pipeline |
| Evaluation/calibration | preprocessing, matching, threshold optimization, metric counts, AP, PR, result rows | test_trace_compute; existing scientific/evaluation suites |
| Comparison/reporting | application paired scoring/bootstrap; reporting workbook/dashboard/plot/render/save, developer/business builders and class-count layout compaction | comparison/reporting suites; paired native pipeline; merged report-layout tests in TRACE mode |
| ClearML startup/configuration | task creation, task/model lookup/naming, sanitized configuration prepare/connect/record/replay | test_trace_clearml; session/models/naming suites |
| Downloads/model verification | checkpoint/threshold downloads, model reopen/readback/metadata/waits/hash verification | test_trace_clearml; native model suite and real downloaded checkpoints |
| Final publication | finalizers, CSV assembly/write, each upload, wait/flush/reload/verify, close/readback/mark status, temporary cleanup | test_trace_clearml; stalled-close subprocess; native terminal readback |
| FiftyOne | backend import/list, snapshot/predictions/evaluations/source hash, lock acquire, dataset load/create, aggregate samples/overlays, native evaluation register/write/save | test_trace_fiftyone; current publication suite; real fresh-process persistence |
| Diagnostic mechanics | operation ordering/nesting/outcomes/task IDs, redaction/scalar bounds, heartbeats/stacks, fork/startup failure/cleanup, independent output | test_tracing and test_trace_subprocess |

## Deliberate aggregate scopes and exclusions

- Core scientific calculations have no logging dependency. Application bootstrap and
  adapter calculation scopes expose their active location through the watchdog.
- Image/detection/row/class loops use aggregate spans and existing progress signals.
  No per-image or per-detection tracing; DDP empty polling emits no lifecycle events.
- SDK lazy properties remain within model-selection/verification spans; stack sampling
  identifies a blocked property without adding wrappers to SDK objects.
- Context managers are instrumented around execution/cleanup, not generator creation.
  Cache lock acquisition ends before the held lifetime, which intentionally includes
  native consumption. FileLock release retains the original context protocol.
- Pure schema/config constants, cheap path calculations, package initializers, scientific
  records and static FiftyOne panel rendering are not individually instrumented.
- Native C/CUDA stack frames and unscheduled Python interpreters remain outside sampling
  guarantees. Diagnostics add no timeout, retry, native cancellation or allocation policy.
