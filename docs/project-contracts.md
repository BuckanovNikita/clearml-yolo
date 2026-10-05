# Project contract summary

Read this summary before changing command, configuration, output, tracking or evaluation
behavior. Use the [current contract index](current-contracts.md) for maintained requirements
and implementation evidence by topic; this summary does not replace those contracts.

`cy` runs the pipeline; `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, and `cy-ground-truth` run individual stages.

Nine entrypoints: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth`, and `cy-init-config`.
`cy-init-config DIRECTORY [--force]` writes editable examples for the eight execution
commands without creating a ClearML task.

Native model settings use top-level Hydra groups `ultralytics` and `ultralytics_predict`
for all model commands. The shared group covers detection-relevant installed upstream defaults; prediction
inherits applicable values through visible configuration references, preserving explicit nulls
and overrides. Prediction execution reads only its resolved group. Project defaults are
imgsz=960, compile=true and nms=true; prediction uses conf=0.001, batch=1, rect=true and
save=false. Native normalization is recorded separately from requested values.
Generated `ultralytics/default.yaml` and `ultralytics_predict/default.yaml` contain native
keys without wrapper indentation and preserve original comments. Use ordinary overrides
such as `ultralytics.epochs=10` and `ultralytics_predict.batch=8`.
Stage-irrelevant settings are commented in exported native YAML and excluded from execution.
Raw `cfg` loading, non-null native `cfg`, nested stage-native mappings and duplicate native
comparison inference settings are unsupported and fail ordinary strict validation.
Effective native YAML and retained prediction manifests support replay; YAML is retained
locally with comments preserved; canonical run/dataset/report configurations and native General
parameters support ClearML replay without artifact copies.
Pass device, batch, AMP, compilation and native augmentation options through the native groups.
The five model commands use a user-wide, same-OS FIFO scheduler for whole NVIDIA GPUs. Demand
comes only from native device settings: a training integer is one GPU, a list uses its length,
each automatic `-1` contributes one without binding that written ID, null/empty/`cuda` is one,
and `cpu`/`mps` is zero. GPU inference is one device. A pipeline reserves the maximum of training
and enabled GPU-inference demand before starting.

Admission is strict head-of-line FIFO and reserves N devices atomically; later requests do not
bypass a blocked valid head, while successive heads may run concurrently when each fits. A demand
larger than the supported visible set fails before enqueue. NVML excludes external compute users
and unknown telemetry fails closed. Inherited visibility is mapped to stable UUIDs in an isolated
metadata subprocess. Waiting precedes ClearML task creation and native GPU context. Each admitted
fresh child owns one task and receives concrete child-local native devices; requested and effective
device records remain separate.

After verified training and telemetry-confirmed DDP cleanup, a pipeline retains its first assigned
GPU, atomically releases N-1, and routes GPU prediction and comparison to local device 0. The first
remains reserved until child exit, including CPU-only downstream work. The scheduler has no daemon,
TTL/PID-only reclaim,
priority, bypass, separate count setting, MIG support, or cross-host/cross-OS coordination. The
project still does not provide batch tuning, custom augmentation JSON, `--force-gpu`, or disabled
tracking. Unsupported options fail rather than being silently ignored.

The five model commands default to the queue-aware local Hydra launcher for BasicSweeper. It starts
fresh children as FIFO capacity permits, preserves callbacks, job environment, per-job directory
and chdir behavior, and returns ordered `JobReturn` statuses. Any failed child makes the invocation
nonzero and releases its reservations.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for evaluation. Pipeline
comparison uses test; standalone `cy-compare` defaults to test and accepts a split override.
Both models use identical current images from that split and matching inference settings.
Reports consume their paired results and manifest split from `comparison_dir`. Historical
dashboards provide only stored thresholds under the maintained
[task recovery contract](../specs/012-remove-legacy-compatibility/contracts/task-recovery.md),
with a warning about rounding and unavailable calibration provenance; their predictions/metrics
are not comparison inputs. Explicit threshold maps take precedence. Ordered task recovery
accepts named threshold payloads, then dashboards; present malformed sources fail strictly.
Weights prefer uniquely identified best Output Models, then the logged last registered model;
only tasks without Output Models use ordered checkpoint artifacts. One selection supplies
weights and truthful source task/model or task/artifact provenance without invented model links.
Current comparison settings remain authoritative; source configurations are not imported.
Available threshold precision is preserved, but historical architecture loading is not guaranteed.
The automatic baseline is the latest completed prod-tagged task excluding the current task;
missing automatic baseline skips comparison, while invalid explicit references fail.

ClearML is required for execution commands. One execution invocation owns exactly one task;
nested stages reuse it and workers do not create tasks or upload artifacts.
The invocation-owned task forwards normal stdout and stderr to its ClearML Console while it
is active, including native YOLO output. Console streams are raw; credential sanitization
applies to published configuration. Argument-parser and framework auto-capture remain
disabled, and forwarding does not cover output after task closure or guarantee capture of
DDP subprocess streams.
Complete a task only after all required artifacts and the native best Output Model
are uploaded, verified and flushed. Fail task and command on computation, upload, flush, or interruption
errors while retaining local output. Keep credentials out of published configuration and
failure status. Native owner-only training/validation image previews are permitted.
FiftyOne visualization is optional: setup and publication errors warn and cannot fail
otherwise successful computation or the ClearML task. Required artifacts/model uploads
and flush verification retain their failure behavior.
Use the shared CSV-addressed dataset cache outside run outputs; source images are immutable.
Standalone `cy-train` requires `ground_truth`; prepared dataset paths returned by training are
always present. Direct native-dataset training and native staging are not supported.
