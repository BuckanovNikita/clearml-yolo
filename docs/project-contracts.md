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
Pass device, batch, AMP, compilation and native augmentation options directly to Ultralytics.

The project no longer provides GPU scheduling, filesystem queues or leases, batch tuning,
custom augmentation JSON, `--force-gpu`, or disabled tracking. Removed options must fail
rather than be silently ignored.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for evaluation. Pipeline
comparison uses test; standalone `cy-compare` defaults to test and accepts a split override.
Both models use identical current images from that split and matching inference settings.
Reports consume their paired results and manifest split from `comparison_dir`. Historical
dashboards are not comparison input. Source task/model links provide provenance; comparison
retrieves weights and exact thresholds, without importing source configurations over the
current comparison settings.
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
