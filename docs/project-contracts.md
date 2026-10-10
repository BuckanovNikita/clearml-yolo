# Project contract summary

Read this summary before changing command, configuration, output, tracking or evaluation
behavior. Use the [current contract index](current-contracts.md) for maintained requirements
and implementation evidence by topic; this summary does not replace those contracts.

`cy` runs the pipeline; `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, and `cy-ground-truth` run individual stages.

Entrypoints: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth`, `cy-init-config`, and `cy-dedup`.
`cy-init-config DIRECTORY [--force]` writes editable examples for the eight execution
commands without creating a ClearML task.
`cy-dedup [DIRECTORY] [--dry-run]` is local cache maintenance without application startup
or tracking. It reflinks identical same-named images, preserving paths and content;
unsupported reflinks are reported skips. See the
[deduplication contract](../specs/018-cache-image-dedup/contracts/cli.md).

Python imports follow `core`, `application`, `adapters` and `entrypoints` boundaries.
Public workflows receive explicit typed dependencies from CLI composition; Hydra
conversion and external SDK access stay outside the application. Pandera owns pure
stage validation, with storage adapters retaining lexical input handling and original
rows. Evaluation adapters retain the pinned scientific algorithms and convert outputs
to project-owned records; reporting adapters generate the original artifacts.
The [Python import migration](python-import-migration.md) documents the module cutover,
explicit programmatic dependencies and regeneration of saved YAML targets. Command
names, ordinary overrides, CSVs and durable output/publication contracts retain their
existing behavior.

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
The five model commands poll whole-NVIDIA-GPU availability before native execution and ClearML
initialization, then execute in the calling process. Demand comes only from native device
settings: a training integer is one GPU, a list uses its length, each automatic `-1` contributes
one without binding that written ID, null/empty/`cuda` is one, and `cpu`/`mps` is zero. GPU
inference is one device. A pipeline waits for the maximum of training and enabled GPU-inference
demand. There is no separate count setting.

An isolated metadata subprocess maps inherited visibility to stable UUIDs without initializing
CUDA in the invoking process. NVML excludes other compute users and unknown telemetry fails
closed; only the invoking PID is ignored so sequential jobs can reuse their own retained context.
Demand exceeding the supported visible whole-GPU set, unsupported MIG and lost visibility fail
clearly. Selected logical indices follow inherited visibility order; `CUDA_VISIBLE_DEVICES` is
not rewritten. Training uses all selected devices required by its demand, and GPU prediction,
validation and comparison use the first selected device. Native training-memory cleanup remains.
Requested settings and effective devices are recorded separately under `gpu_selection`.

There are no tickets, reservations, queue registry, worker supervision, FIFO fairness or exclusive
allocation guarantees. Simultaneous commands may observe the same free GPU. Historical queue data
is untouched and unused. CPU/MPS and non-model commands bypass GPU telemetry. The project does
not provide batch tuning, custom augmentation JSON, `--force-gpu`, disabled tracking or MIG
support. Unsupported options fail rather than being silently ignored.

Local Hydra multiruns use the standard sequential BasicLauncher with BasicSweeper, preserving
callbacks, job environment, per-job output directory, configured chdir and normal exceptions.
The [GPU execution contract](../specs/022-simple-gpu-wait/contracts/execution.md) supersedes
feature 013 queue requirements and the queue-specific constitution amendment; their dated
history remains evidence of the former design.

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

Evaluation publication follows the
[current result contract](../specs/014-evaluation-publication/contracts/publication.md):
one invocation-owned `gt_csv` and combined `predicts_csv` retain original source rows,
stable IDs, exclusions, thresholds and JSON pre/post-threshold relationships. Canonical
CSVs assemble once before completion; prediction-only rows stay not evaluated.
Publish original full/DTRK dashboards, exact validation thresholds and paired comparison/
report workbooks with comparison exclusions. Duplicate evaluation summaries and separate
match/threshold/methodology sidecars remain local. Missing automatic baseline retains
candidate dashboards/plots and records its skip reason.

Current-model `Confusion matrix` charts select Counts, Row %, Column % or Overall %,
preserving exact post-threshold counts, true-row/predicted-column orientation, class
order/background and explicit zero denominators. `Precision-recall` combines all class
traces on test only, with AP/method legends and confidence/cumulative TP/FP hover.
Class PR uses the geometry-valid authoritative AP50
population, confidence ordering and public matching; it is distinct from frozen-threshold
confusion counts. Empty predictions with GT have AP50 zero; absent GT has unavailable
recall/AP; null-gap traces retain explicit class-legend status without numerical points. Visible labels
use model name/split without internal IDs or hashes. Invocation-local checkpoint/split
slots repeat; model/context fallback and readable stage/ordinal suffixes prevent collisions.
Baseline charts and comparison tables are excluded from Plots; baseline rows/dashboards,
paired workbooks and headline single values remain published. Native callback validation
PR images are excluded while other native output and DDP owner replay are preserved.
See the [readable plot contract](../specs/020-readable-evaluation-plots/contracts/plots.md).

Project-local exact task/model name collisions, including archived records, receive a
shared readable suffix after rechecking; unused requested names and output paths remain
unchanged. Owned best models may receive full-precision validation thresholds only when
calibration provenance matches the checkpoint actually used for prediction and remote
readback verifies the metadata. Standalone metrics never creates or modifies models.

ClearML is required for execution commands. One execution invocation owns exactly one task;
nested stages reuse it and native DDP descendants do not create tasks or upload artifacts.
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
otherwise successful computation or the ClearML task. Project-owned caught-error
logging includes redacted operation/context and cause summaries, with stack locations
at DEBUG (the existing default); INFO omits those stacks. Diagnostic stacks exclude
locals and source excerpts. Opaque configuration payloads and failure-status fields
retain conservative suppression. Required artifacts/model uploads
and flush verification retain their failure behavior.
Use the shared CSV-addressed dataset cache outside run outputs; source images are immutable.
Standalone `cy-train` requires `ground_truth`; prepared dataset paths returned by training are
always present. Direct native-dataset training and native staging are not supported.


Opt-in `LOGURU_LEVEL=TRACE` diagnostics identify blocking operations through lifecycle
records, 30-second deepest-operation heartbeats and 60-second changed grouped Python
thread snapshots. The watchdog writes to captured stderr independently of Loguru;
caller sinks are preserved. Diagnostics use bounded redacted scalar context and
location-only stacks, without configuration/data/locals/source dumps. Execution policy,
GPU availability semantics and failure propagation stay unchanged. Command tracing
covers cleanup and ends with `command.return`, which is not a success assertion.
Application workflows use the execution-resource tracing port; evaluation and FiftyOne
adapters may import the observability adapter. See [diagnostics](diagnostics.md) for
capture, record interpretation, output bounds and native scheduling limits.
