# Project contract summary

Read this summary before changing command, configuration, output, tracking or evaluation
behavior. Use the [current contract index](current-contracts.md) for maintained requirements
and implementation evidence by topic; this summary does not replace those contracts.

`cy` runs the pipeline; `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, and `cy-ground-truth` run individual stages. `cy-export` exports and verifies
Faster R-CNN deployment bundles. The `cy-batch-estimate` utility measures local
synthetic training capacity without a ClearML task. Memory-guided candidate selection
retains full trials and confirmation; independent cases can run on separate idle
selected GPUs, with `--jobs` controlling concurrency. See
[its contract and acceptance limits](batch-estimation.md).

Entrypoints: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth`, `cy-export`, `cy-init-config`, `cy-dedup`,
`cy-batch-estimate`, `cy-docs`, and `cy-queue`.
The `cy-queue` command belongs to the separately installed compatible queue source
package; CY's own entrypoints do not require that package or its configuration.
`cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]` writes one selected
execution wrapper (default `cy`), a local command base and every application YAML
referenced by their defaults, without a ClearML task. Private schema names are
separate from public YAML names; legacy trees remain supported. Default
YOLO model commands retain both native groups. New detector selections write one model
preset YAML; non-model commands require neither. Export defaults to Faster R-CNN ResNet-50-FPN.
See [selected export and runtime isolation](runtime-isolation.md).
`cy-dedup [DIRECTORY] [--dry-run]` is local cache maintenance without application startup
or tracking. It reflinks identical same-named images, preserving paths and content;
unsupported reflinks are reported skips. See the
[deduplication contract](../specs/000-baseline/spec.md#explicit-cache-deduplication).

`cy-docs [--port PORT] [--no-browser] [--check]` opens the packaged Russian reference
and tutorials on loopback. Its catalog derives fields and effective defaults from
the installed declarations. Configuration editing and isolated composition previews
produce YAML and commands for terminal execution; they do not launch workflows or
resolve external inputs. `--check` verifies the catalog, assets, links and tutorial
composition cases without starting a server. Documentation failures stay within
documentation operations. See the [local documentation contract](local-documentation.md)
for preview restrictions, completeness checks and maintenance ownership.

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

The default `model=ultralytics` retains top-level Hydra groups `ultralytics` and
`ultralytics_predict`. The shared group covers detection-relevant installed upstream defaults; prediction
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
locally with comments preserved; CLI canonical run/dataset/report configurations retain full
replay settings without artifact copies, while native General contains scientific experiment
parameters. YOLO replay applies scientific General overrides over full `run.ultralytics`
settings; devices and other known execution-only values remain in the full configuration.
External controllers can explicitly normalize cache identity before job creation through
the [stable parameter contract](../specs/000-baseline/spec.md#stable-experiment-parameters-and-controller-caching).
Pass device, batch, AMP and compilation through the native groups. Native augmentation
options retain their behavior with `transforms=default`. For `cy` and `cy-train`,
`transforms=albumentations transforms.pipeline_file=FILE` selects standard `A.save`
JSON for any registered backend. The custom profile visibly disables optional native
augmentation, reports conflicting overrides and retains required final preprocessing.
One first top-level JSON Mosaic receives raw training donors on every backend.
Validation rejects unsupported transforms, targets and preprocessing conflicts; a
canonical content snapshot and SHA-256 digest make replay independent of the source
file. Generated training configurations include both profiles and the selected
model/profile specialization. See the [augmentation contract](augmentation.md).
Direct `cy` and stage commands execute their configured native devices without queue
storage, reservations, waiting or automatic substitution. Explicit training `batch=null`
inspects actual hardware and dataset limits for strict saved-estimate lookup. It
prefers an exact-allocation measurement, otherwise derives an explicitly extrapolated
global batch from compatible single-GPU measurements for every hardware type/capacity.
Requested null remains in replay; chosen values, target allocation and source
keys, boundary/ceiling/numerical status and diagnostics are recorded separately.
Discovery-time nonfinite computation after a fully successful under-budget candidate
permits one fresh repeat of that last good batch. Only a full successful repeat
yields usable `numerically_limited` evidence; every failed confirmation remains
failed. Numerical failure never bounds memory or establishes a capacity maximum.
Exact lookup and extrapolation retain numerical limitations ahead of ceiling and
validated status. Schema-1 catalogues remain readable; saves write schema 2, which
requires upgraded readers, and read-only access never rewrites historical files.
Pending snapshots remain failed with null batches until confirmation succeeds.
Training never retries OOM with a hidden batch reduction. Numeric defaults and existing YOLO AutoBatch values keep their behavior. `cy -m`
uses sequential BasicLauncher. `queue.*`, `autogpu.*` and the former queue launcher
are rejected with migration guidance. The separate [cy-queue contract](queue.md)
owns count/exact submissions, complete sweep expansion, owner workers, per-host ordering,
training allocations with acknowledged contraction to the first inference GPU, and
guardian recovery. No training-finished notification retains the full allocation;
failure after durable contraction does not restore released GPUs, and cleanup/recovery
uses the remaining claim. External guardians own queued descendant cleanup outside ClearML
finalization; supervisor uncertainty retains recovery evidence without retroactively
failing a completed successful task. Recovery still requires conservative ownership proof;
stale unlocked records alone do not veto GPU admission.
Queue allocation preserves explicit
CPU phases, compilation, AMP, batch and model settings. Inference uses the first allocated
device. Automatic GPU availability uses only used VRAM strictly below the configured
`queue.max_used_memory_gib` (default 2.0 GiB). The worker freezes this positive finite
threshold in each guardian payload for the fresh check immediately before launch;
equality is unavailable. Current queue allocations and explicit holds remain exclusive
unless released. The threshold does not guarantee that compilation/training fits.

Each direct or queued multirun adds one shared readable `multirun-<UTC date/time>-<word phrase>` ClearML
tag to all its jobs, preserving explicit tags. The group is fresh per launch/submission
and persists in queued snapshots. Effective MULTIRUN mode includes one-job sweeps;
ordinary RUN adds no tag. See the
[grouping contract](../specs/000-baseline/spec.md#direct-execution-shared-queue-and-diagnostics).

The `model=deimv2/<preset>`, `model=rfdetr/<preset>`, `model=fasterrcnn/<preset>` and
unreleased `model=fcos/<preset>` groups
own typed `model.train` and `model.predict` settings. Unsupported controls fail explicitly.
Changed controls in inactive groups are rejected in both directions; YOLO settings belong
in `ultralytics`/`ultralytics_predict`, and native settings belong in `model.train`/`model.predict`.
Their composition derives immutable COCO datasets from the same validated CSV records;
public labels retain exact strings and exclude detector background slots. A descriptor
embedded in each owned checkpoint binds backend, preset, foreground vocabulary,
preprocessing and source/dependency identity; its external record adds the checkpoint hash.
See the [backend contract](../specs/000-baseline/spec.md#detector-backends-and-deployment-export) and
[model guide](multi-model-backends.md) for presets, pretrained sources and limitations.
Native multi-GPU training uses one supervised rank per GPU, with global microbatches
divisible by world size and one invocation-owned ClearML task. FCOS uses zero-based
foreground labels and P3–P7 features; Faster R-CNN retains its label offset. Native
GPU and real multi-GPU acceptance for these additions remain pending.

Comparisons resolve each checkpoint independently, including YOLO/native pairs. Raw native
references require explicit backend, preset, foreground labels and preprocessing; assertions
cannot replace conflicting embedded metadata. Two references to the same checkpoint must
agree on its resolved model metadata; their display labels and thresholds may differ.
Cache identity includes those assertions.
The shared comparison device and inference controls remain authoritative, with each backend's
effective preprocessing recorded. Replay cannot switch between the YOLO and new-detector
runtime families after initialization; relaunch with the requested selection instead.

`cy-export` has separate CPU/FP32 ONNX, GPU engine-build and GPU verification operations.
It publishes graph/engine metadata and verification evidence under one task without another
trained Output Model. The [export contract](tensorrt-deployment.md)
defines both dynamic profiles, standalone execution and numerical/quality gates. Verification
uses a fixed labeled corpus with source-byte and actual evaluator identity. Local execution
does not establish CUDA 11.8 target compatibility; consult dated acceptance evidence.

Queue inventory uses NVML and a metadata-only visibility probe before native launch.
Unknown required-device telemetry, visible MIG and damaged coordination state fail closed.
Direct execution has no dependency on this machinery. Queue workers execute only their
own UID's jobs. Every local participant may reorder pending jobs; only owners cancel/recover.
Each host partitions durable shared NFS metadata independently; host-global local UUID locks
prevent participating roots from allocating the same device. Physical-index operator
controls need no tokens, reasons, force flags or confirmation. `gpu free INDEX` and
`gpu release INDEX` immediately clear that GPU's reservations and existing holds across
roots, without memory/process checks, signals or access to the original queue directory.
Per-device reservation generations preserve sibling allocations and fence older guardian
writes, handoff, recovery and cleanup. Freeing leaves processes and job outcomes unchanged
and grants no persistent admission bypass. Public queue output uses physical indexes or
word aliases for absent devices; full GPU UUIDs and claim tokens remain internal. Guardian
death retains recovery records, but stale unlocked records alone do not block capacity.
No automatic retry is made for uncertain outcomes. Historical 013/022/024 specifications
remain preserved as prior intent.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for evaluation. Pipeline
comparison uses test; standalone `cy-compare` defaults to test and accepts a split override.
Both models use identical current images from that split and matching inference settings.
Reports consume their paired results and manifest split from `comparison_dir`. Historical
dashboards provide only stored thresholds under the maintained
[task recovery contract](../specs/000-baseline/spec.md#evaluation-comparison-and-historical-model-recovery),
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
[current result contract](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle):
one invocation-owned `gt_csv` and combined `predicts_csv` retain original source rows,
stable IDs, exclusions, thresholds and JSON pre/post-threshold relationships. Canonical
Ground truth uploads when validated and written; the combined prediction CSV assembles
once when all enabled contributors finish, before later reports. Prediction-only rows stay not evaluated.
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
See the [readable plot contract](../specs/000-baseline/spec.md#reports-and-readable-visualization).

Project-local exact task/model name collisions, including archived records, receive a
shared readable suffix after rechecking; unused requested names and output paths remain
unchanged. Owned best models may receive full-precision validation thresholds only when
calibration provenance matches the checkpoint actually used for prediction and remote
readback verifies the metadata. Standalone metrics never creates or modifies models.

ClearML is required for execution commands. One execution invocation owns exactly one task;
nested stages reuse it and native DDP descendants do not create tasks or upload artifacts.
FD-level project capture retains stdout/stderr from Python, native writes and DDP children.
A network-independent terminal mirror and attach-only publisher serve the existing task;
the publisher creates no task and changes no task state. Required console/scalar publication
uses approximately two-second batches and a bounded final-offset barrier. Local logs survive
failure; incomplete required publication fails the command without replacing an original
computation error. No automatic replay of uncertain deliveries occurs. Prediction explicitly
uses verbose=false and one rate-limited operation progress indicator across supported backends.
Complete a task only after all required artifacts and the native best Output Model
are uploaded, verified and flushed. Fail task and command on computation, upload, flush, or interruption
errors while retaining local output. Keep credentials out of published configuration and
failure status. Native owner-only training/validation image previews are permitted.
FiftyOne visualization is optional: setup and publication errors warn and cannot fail
otherwise successful computation or the ClearML task. Fresh isolated workers bound imports,
publication and shutdown with finite positive preflight/publication/lock timeouts of 60/900/30
seconds; success requires zero exit and a matching complete receipt. See
[runtime isolation](runtime-isolation.md). Project-owned caught-error
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

Project paths follow [filesystem ownership](filesystem-policy.md): `CY_HOME` owns outputs
and the CSV dataset cache, while SDK configuration/cache/defaults remain discoverable
through their normal environment and user settings. Explicit preparation and YOLO
estimator setup persist an absolute Ultralytics `weights_dir` before catalogue reuse
or worker startup: relative values resolve against invocation cwd; existing absolute
values are retained. CY coordinates through an adjacent settings-file lock, verifies
readback and synchronizes live SDK `weights_dir` and `WEIGHTS_DIR`, without rewriting
already-correct settings or changing unrelated disk settings, process-only callback
switches or cached files. Imports, help and configuration inspection remain inert.
Rerun `cy-download-weights` once from the original preparation directory to migrate
an older relative cache, reusing valid files. Errors identify the settings file and
JSON/permissions/retry recovery. Other external selectors stay unchanged.
Explicit model preparation may write model assets,
locks, temporary sibling downloads and native HF metadata into configured native caches
outside `CY_HOME`; preparation receipts and all project outputs remain contained.
`cy-download-weights` retries the eligible catalogue and exits nonzero on incomplete
preparation. Valid native assets precede the packaged `weights-*` release pin. Bulk
preparation never falls back to original model hosts; release failures retain safe
archive diagnostics. GHR is a GitHub Files remote and GH a separate VCS remote used
by ordinary selected-model source resolution. Independent tar archives and members require size/SHA-256
validation and safe paths before native publication; HF restoration includes real
snapshot/configuration metadata without an upstream metadata request. Original source
identities remain provenance. Weight releases have their own cadence; code releases
reuse the pin without uploading assets. Actual `cy` alone performs the
once-per-catalogue/manifest/location bulk attempt,
including completed partial failures; help, inspection, submission and standalone
stages do not. See [model preparation](model-assets.md) for exclusions and recovery.
Project temporary files receive explicit retained invocation arenas; global SDK temporary
settings are unchanged. Startup performs no scratch recovery or recursive deletion. Native
ClearML callback switches restore in memory without persisting user settings, including
fresh DDP trainer scopes. Invalid dataset entries remain available for deliberate idle
maintenance; unsupported native locks fail without a soft-lock fallback.

Queue public summaries show owner, order, state, requested/allotted devices, wait reason,
progress and ClearML link without exposing private executable configurations. See
[queue operations](queue.md) and [diagnostics](diagnostics.md#gpu-admission-decisions).

Queue settings remain mandatory: each user fills their XDG config file (normally
`~/.config/clearml-yolo/queue.toml`); explicit absolute `CY_QUEUE_CONFIG` overrides it.
Both metadata and coordination roots are explicit. Coordination supports eligible
NFS mounts with host-local flock as described in the
[queue contract](queue.md#nfs-coordination). Each host binds one coordination location
across users and queues. Archive/restore is owner-only, preserves durable history and
keeps recovery-required jobs visible; stable `job-N` numbers never depend on view position.
Human-facing output uses readable names and references across CLI, TUI, diagnostics,
console publication and reports. Exact IDs/hashes remain in machine provenance,
explicit JSON, raw captures and link targets; see [readable output](readable-output.md).

Startup `run`/`run_overrides` views and early training General follow the
[configuration contract](../specs/000-baseline/spec.md#configuration-resolution-and-replay).
Selected executable inputs remain distinct from observed normalization and result provenance.
