# Technical reference

Start with the [Russian usage guide](README.md) for training and complete experiments.
This reference covers setup and operational details. The
[current contract index](docs/current-contracts.md) identifies authoritative contracts
and implementation evidence; historical feature evidence records what was checked at
that time, not necessarily the current interface.

## Setup

Use Python `>=3.12.13,<3.14` (Python 3.12.13 or newer in the 3.12 series, or
Python 3.13) and an available project checkout. See [package metadata](pyproject.toml)
and the [compatibility policy](docs/development.md#python-compatibility). Populate the approved `digital-metrics` and `report-generator`
source copies using [external dependency setup](docs/development.md#external-dependencies),
then install from the committed lockfile:

```bash
uv sync --frozen
```

The lockfile refers to ignored editable source directories under `external/`; a fresh
checkout does not download those source trees or enforce their Git revisions.
Do not change approved upstream revisions as part of setup. Development dependencies
and local source overrides are documented in the development guide.

Install the extras needed for the intended operation:

| Capability | Installation from the project checkout |
| --- | --- |
| DEIMv2, RF-DETR, Faster R-CNN | `uv sync --frozen --extra detectors` |
| Faster R-CNN ONNX export | `uv sync --frozen --extra detectors --extra export` |
| Queue terminal interface | `uv sync --frozen --extra queue-ui` |

Combine extras when needed; for an already prepared optional environment, use the
[development environment preservation guidance](docs/development.md#python-integration-and-architecture).
The detector stack requires Torch >=2.13.0 and Torchvision >=0.28.0; consult `uv.lock`
for the selected versions. DEIMv2 also requires the exact source revision and compatible
assets in the [model guide](docs/multi-model-backends.md#deimv2-source-and-initialization).
TensorRT and its matching CUDA runtime are separate requirements in the
[deployment guide](docs/tensorrt-deployment.md).

Configure ClearML credentials, endpoints and remote artifact storage through the SDK's
normal configuration. All execution commands require ClearML; there is no
`clearml.enabled=false`. `clearml.output_uri=true` is the default; null, false and
empty destinations are rejected. Supply project, task name and tags explicitly.
`cy-init-config`, `cy-dedup` and queue administration do not create experiment tasks;
queued execution does. The standalone TensorRT runner also does not create a task.

Direct execution and shared queue supervision require supported Linux process ownership
facilities, including `os.pidfd_open` and access to relevant `/proc` records. Preflight
reports an incompatible interpreter before native work. See
[runtime prerequisites](docs/runtime-isolation.md) and [queue requirements](docs/queue.md).

## Configuration and migration

CLI entrypoints are declared in [pyproject.toml](pyproject.toml); Hydra schemas are
registered in [configs.py](src/clearml_yolo/entrypoints/hydra/configs.py).
`cy-init-config DIRECTORY --command COMMAND` exports only the selected command
(default `cy`). YOLO model commands export both native groups; table-only commands
export their wrapper. `--model backend/preset` selects a registered detector tree;
`cy-export` defaults to Faster R-CNN. Preserve generated `defaults` when editing.

Existing selected files cause an error. `--force` replaces ordinary selected files,
leaving other command files alone. Back up customized YAML before regeneration:

```bash
cp -a cy-config cy-config.backup
cy-init-config cy-config --force
```

Repeat with `--command` for other wrappers, then transfer user values into the new
files. Old `_target_` paths under `clearml_yolo.tasks`, `clearml_yolo.apps` and former
modules are unsupported. The [Python migration guide](docs/python-import-migration.md)
lists replacements. CLI names, ordinary Hydra overrides and CSV/result interfaces
remain the supported public workflow.

YOLO training uses `ultralytics.*`; prediction uses `ultralytics_predict.*`.
Other detectors use `model.train.*` and `model.predict.*`. In each exported group
file, use bare keys rather than another wrapper. Unknown settings and changed inactive
backend controls fail validation. Raw `cfg`, nested stage-native mappings and duplicate
comparison inference fields are unsupported. Use the
[native configuration contract](specs/005-explicit-detection-config/contracts/native-configuration.md)
for inheritance and precedence.

| Existing manual step or parameter | Corresponding interface |
| --- | --- |
| Prepare native training data | Supply CSV through `ground_truth`; preparation owns native data and class selection |
| Ultralytics `model`, `epochs`, `batch`, `imgsz`, `amp`, `mosaic` | Corresponding `ultralytics.*` keys |
| Ultralytics prediction `batch`, `conf`, `iou` | Independent `ultralytics_predict.*` keys |
| Native `project` and `name` | Pipeline `run_dir` and explicit ClearML project/task identity |
| Manually export detections | `cy-predict` produces canonical prediction CSVs |
| Run digital-metrics and freeze thresholds | `cy-val` or `cy-metrics`; calibration is on `val` |
| Evaluate two checkpoints on current data | `cy-compare` with per-model frozen thresholds |
| Run report-generator | `cy-report` consumes the paired comparison directory |
| Wire all stages and tracking in a script | `cy` runs stages under one task |

Project YOLO defaults include `imgsz=960`, `compile=true` and `nms=true`.
Prediction defaults include `conf=0.001`, `batch=1`, `rect=true`, `save=false`;
image size is inherited unless overridden. These prediction filters are distinct
from calibrated evaluation thresholds. CSV policy controls native `data`, `classes`,
`fraction` and `single_cls`. `resume` is rejected: start a new training run from
existing weights. Compare library versions, exact splits and effective training/
inference settings when reproducing a manual run.

Direct commands pass native devices without queue admission, reservation or waiting.
Do not interpret `device=-1` as a project scheduler; its handling belongs to the
selected backend. YOLO native DDP accepts a device list, with a separate inference
device. Other detector adapters accept CPU or one CUDA device. Direct Hydra sweeps
are sequential. Every multirun adds one shared `multirun-<UUID>` tag while preserving
user tags; a single ordinary invocation adds none. See
[the tag contract](specs/030-multirun-tags/contracts/tags.md).

`--help` and `--cfg job --resolve` avoid workflow execution and ClearML task creation,
but startup may create local scratch/logs. Use an existing isolated `CY_HOME` for
configuration checks. Composition does not prove input existence, checkpoint loading,
GPU capacity or successful publication.

## Inputs and evaluation

Training requires `ground_truth` and nonempty `train`/`val`; the default pipeline
also consumes `test`. CSV image paths resolve relative to the CSV directory, while
CLI input paths resolve from the launch directory. Image identities, background rows,
invalid boxes and split ownership follow the
[CSV training contract](specs/004-ground-truth-training/contracts/cli.md).
YOLO supports prepared `ndjson` (default) or `flat` data; other detectors derive COCO
inputs. Direct native-dataset training is not an alternative to the CSV interface.
Source images remain immutable and are not uploaded as raw dataset artifacts.

Prediction CSV columns are `image_name`, `instance_label`, `confidence`,
`bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`. Validation, metrics and comparison
warn and remove invalid prediction geometry from the evaluation copy, preserving
raw CSV evidence. All-invalid predictions are scored as empty, with unmatched truth
counted as false negatives. See [evaluation safety](specs/001-release-030/contracts/cli.md#evaluation-input-and-output-safety).

`cy-val` and `cy-metrics` calibrate on `val`; thresholds are frozen for evaluation.
Standalone comparison defaults to `test` and can select another present split.
Both models use the same current images and shared inference controls, while their
own compatible preprocessing is recorded. Automatic baseline selection uses the
latest completed `prod` task in the project, excluding the current task. Missing
automatic baseline skips comparison/reports; invalid explicit references fail.

Local ModelRef values need weights, exact per-class thresholds and fallback labels
when identity is unavailable. External native weights without embedded descriptors
also need backend, preset, ordered foreground labels and preprocessing. Assertions
cannot override conflicting metadata. See
[checkpoint metadata and comparison](docs/multi-model-backends.md#data-checkpoints-and-comparison).
ClearML recovery selects weights and threshold sources in a defined order;
historical dashboards supply stored thresholds, never historical predictions or
metrics for current comparison. See the [task recovery contract](specs/012-remove-legacy-compatibility/contracts/task-recovery.md).

## Provenance and publication

One execution invocation owns one ClearML task. Pipeline stages reuse it; native DDP
children do not create tasks or upload. Completion requires verified mandatory
artifacts, the native best Output Model where applicable, and publication flush.
Computation, upload, flush or interruption failures fail the command/task while
retaining local output. Optional FiftyOne failure has different semantics below.

The [publication contract](specs/014-evaluation-publication/contracts/publication.md)
is the maintained inventory. It covers canonical invocation-owned `gt_csv` and
`predicts_csv`, original source-row lineage, exclusions, thresholds and JSON evaluation
relationships. Full/DTRK metric workbooks, exact validation thresholds and paired
comparison/report workbooks are published as specified there. Native YAML, NDJSON,
archives, manifests, diagnostic receipts and duplicate evaluation sidecars remain
local. Consumed dataset and explicit report configurations are Configuration Objects,
not artifact copies. Canonical `run` configuration supports replay; see the
[configuration publication contract](specs/009-resolved-config-uploads/contracts/configuration-files.md).

Preserve `<checkpoint>.identity.json` and `<predictions.csv>.provenance.json` when
moving results. Native checkpoint descriptors also record architecture, class order,
preprocessing and source/dependency identity. Hash and metadata conflicts fail.
A fallback label does not invent a training task: results show `Training task:
unavailable` when necessary. Stored provenance takes precedence over labels. For a
Unicode Hydra label, retain internal quoting, e.g. `'model_label="experiment-Ω"'`.

New metric books and reports identify each source model and its full training-task
ID where known. Paired reports identify both models on every sheet and repeat those
labels when printing; width fits one page while row page breaks remain. Compatibility
adapters preserve original metric layouts for report generation and threshold recovery.
Workbook checksums detect edits or resaves; regenerate books rather than modifying
signed inputs. Existing remote artifacts are not rewritten. See
[source identity on new results](specs/014-evaluation-publication/contracts/publication.md#source-identity-on-new-results)
and [report identity](specs/019-model-report-identity/contracts/report-identity.md).

ClearML interactive plot labels use readable model names and splits, without internal
IDs or hashes. Current-model `Confusion matrix` offers Counts, Row %, Column % and
Overall %; `Precision-recall` combines class traces on `test` only, with AP50/method
legends and confidence/TP/FP hover data. Empty classes have explicit status. Repeated
checkpoint/split slots retain labels; collisions gain readable suffixes. Baseline
plots and comparison tables are excluded from Plots, while baseline books, paired
reports and headline comparison values remain available. Native validation PR images
are filtered; other native plots, previews and scalars remain. See the
[plot contract](specs/020-readable-evaluation-plots/contracts/plots.md).

Report summaries show finite-metric class counts, such as `AP50-valid-class-count:
18/20`; finite zero values count. Each model uses its eligible classes and comparison
uses the shared set. `NA` remains an unavailable metric, not a numerical zero.
The maintained [publication contract](specs/014-evaluation-publication/contracts/publication.md)
explains these summaries.

## Filesystem and cache

`CY_HOME` defaults to the launch directory. Project outputs, logs, cache and scratch,
including final symlink destinations, stay inside this root. External inputs and SDK
configuration selectors remain valid. Default results use
`runs/<safe-project>/<safe-task>-<task-id>/`; pipeline `run_dir` owns stage routing.
Do not supply conflicting stage outputs or native project/name values. Standalone
output-producing commands should use fresh destinations.

Prepared CSV datasets live under `.cache/clearml-yolo/datasets/`, outside run outputs.
Project scratch uses retained `.tmp/cy-runtime-*` arenas; `CY_RUNTIME_TEMP_ROOT` can
select another parent inside the project. SDK configuration/cache discovery, `HOME`,
XDG and global `TMPDIR`/`TMP`/`TEMP` are unchanged. No startup recovery scan or recursive
cleanup runs. Scratch remains after success, failure and cancellation; remove selected
old arenas only after their owners and descendants are inactive. Invalid dataset-cache
entries are preserved for deliberate idle maintenance. Unsupported native locks fail
without a soft-lock fallback.

Legacy `$CY_HOME/.config` files and SDK caches are neither moved nor deleted. To use
those existing files deliberately, select them before SDK initialization:

```bash
export CY_HOME="${CY_HOME:-$PWD}"
export CLEARML_CONFIG_FILE="$CY_HOME/.config/clearml/clearml.conf"
export CLEARML_CACHE_DIR="$CY_HOME/.cache/clearml"
export YOLO_CONFIG_DIR="$CY_HOME/.config"
export FIFTYONE_CONFIG_PATH="$CY_HOME/.config/fiftyone/config.json"
```

The selected files must already be valid; commands do not fabricate empty SDK config
or replace SDK constants. Native ClearML callback switches restore in memory without
writing user settings, including fresh DDP trainers. See
[filesystem ownership](docs/filesystem-policy.md).

`cy-dedup` defaults to `$CY_HOME/.cache`. Stop writers first. It groups regular image
files by exact case-sensitive filename (including extension) and equal content,
skipping symlinks. Linux reflink shares data blocks while preserving independent
writes, paths, bytes, permissions, owner, atime/mtime and extended attributes during
replacement; inode/ctime change and reads may update atime. Unsupported reflinks and
cross-filesystem pairs are skipped; unexpected I/O errors produce nonzero exit.

`--dry-run` neither creates/replaces files nor tests reflink support. External paths
are permitted only with `--dry-run`; mutations stay inside `CY_HOME`. Reported file/
duplicate/reflink counts do not measure freed space. Temporary replacement files sit
beside their image and are removed after the operation. SDKs and GPU are not required.
See the [dedup contract](specs/018-cache-image-dedup/contracts/cli.md).

## Queue operations

[Queue documentation](docs/queue.md) owns submission, worker startup, status,
cancellation, reordering, recovery and operator controls. Queue submission freezes
and validates the entire sweep before adding jobs; installation changes require
resubmission. Native GPU selectors must be unset for allocation; explicit CPU phases
are retained. Compile, AMP and batch settings are not silently modified. An allocation
is held until the complete pipeline and its owned descendants exit.

The earliest runnable job on each host is selected, skipping owners without a worker
and requests lacking a complete GPU set. Worker admission defaults to strictly less
than 2 GiB used memory; `--max-used-memory-gib=1.5` changes that ceiling. This is an
admission condition, not an out-of-memory guarantee. Durable state lives under
`CY_QUEUE_ROOT` (default `$CY_HOME/.cy-queue`); host partitions have separate capacity
and ordering. Shared NFS requires consistent UIDs and supported locking/PID visibility.

Users may reorder others' pending jobs, but only execute, cancel or recover their own.
`move` requires the current revision from `list --json`. Guardian death marks
`recovery_required` and quarantines capacity until owner recovery proves cleanup.
Never delete live lock files or reservation records. Whole allocations remain intact.

Submission `--devices` indices are CUDA-visible logical indices, frozen to physical
UUIDs. In contrast, [physical GPU operator controls](docs/queue.md#physical-gpu-operator-controls)
use physical `nvidia-smi` order or full UUIDs. Holds affect new allocations across
queue roots while preserving active work. Release requires owner authority, a current
claim token and a reason; normal release proves cleanup. Forced release is an audited
manual exception, sends no signals and refuses live locks or confirmed live processes.
Upgrade all cooperating workers before using these controls. Consult the guide before
recovery or release rather than deleting coordination files.

Workers log startup, changed job state and a 60-second heartbeat to stderr at INFO
by default. `--log-level DEBUG` adds each poll summary; WARNING suppresses routine
messages. IDs/JSON remain on stdout. Pipeline output stays in the submitting
project's `.cy/queue-logs/JOB_ID.log`. See [worker diagnostics](docs/queue.md#worker-diagnostics).

With `queue-ui`, TUI arrows select rows; `u`/`d`, `t`/`g` and `b`/`a` reorder,
`c` cancels, `r` recovers, and `q` exits without stopping the worker.

## FiftyOne and process ownership

FiftyOne is optional visualization. Use the [viewing guide](specs/006-fiftyone-integration/quickstart.md)
to open the application and inspect detections and full-split digital-metrics panels.
Its isolated worker owns no GPU or ClearML task. Setup/publication errors warn and do
not fail otherwise successful computation. Available controls are
`fiftyone.enabled=false`, `fiftyone.preflight_timeout_seconds=60`,
`fiftyone.publish_timeout_seconds=900` and `fiftyone.lock_timeout_seconds=30`.
Timeout overrides must be finite positive values. Preflight/publication deadlines
include import and exit, followed by separately bounded cleanup. Success requires a
normal exit and complete matching receipt; partial data remains for retry.
`cy-val` does not expose this configuration group.

For direct cancellation, press Ctrl+C and allow owned-process cleanup to finish.
Repeated signals do not interrupt bounded shutdown. Linux pidfd and `/proc` checks
establish ownership; uncertain cleanup must not release queue capacity. These policies,
DDP ownership and publication subprocess boundaries are documented in
[runtime isolation](docs/runtime-isolation.md). The [DDP guide](docs/ddp-testing.md)
contains opt-in physical multi-GPU/NCCL tests; CPU/offline checks do not establish
accelerator or remote-publication acceptance.

## Diagnostics

Default Loguru level `DEBUG` includes location-only diagnostic stacks; `INFO` gives
short messages. Errors include operation, type, cause and bounded relevant paths/IDs.
Secrets are redacted; diagnostics omit locals and source excerpts, and configuration
errors suppress opaque values conservatively. Importing the package preserves caller
logging configuration.

`LOGURU_LEVEL=TRACE` adds operation lifecycle records, 30-second deepest-operation
heartbeats and changed grouped Python-thread snapshots every 60 seconds (up to eight
groups and twelve frames each). Watchdog output goes directly to captured stderr:
capture both streams. The [diagnostic capture recipe](docs/diagnostics.md) preserves
the pipeline's exit status through `tee`. `command.return` marks return after cleanup,
not successful completion. TRACE adds no retries or execution deadlines, and native
calls can delay diagnostic scheduling. Inspect native library output before sharing it.

Python, native and DDP console output is retained in project-local append-only logs.
A network-independent terminal mirror and attach-only publisher feed the existing
ClearML task. Required publication uses bounded final-offset checks; local logs survive
failure, and incomplete mandatory publication fails execution. Predictions use one
rate-limited progress indicator with native verbose output disabled. See
[runtime isolation](docs/runtime-isolation.md) and
[ClearML transport troubleshooting](docs/multi-model-backends.md#clearml-reporting-transport-errors),
including `Task.query_tasks` failures with `tasks=None`.

## Python integration and development

Python use cases live in `application.use_cases` and require an explicit `deps`
argument. The composition root creates a `WorkflowDependencies` bundle; adapters
own SDK, filesystem, rendering and process effects, while core scientific/policy
records remain independent of those effects. Follow the
[import migration table and invocation example](docs/python-import-migration.md),
[import boundaries](docs/import-boundaries.md) and
[shared evaluation/reporting interfaces](docs/shared-evaluation-reporting.md).

For contribution checks, approved dependency revisions, hook side effects, temporary
local-source handling during commits and Git-tag-only release evaluation, use
[development procedures](docs/development.md). Documentation-only changes do not
force a version bump. Native/backend/export acceptance and its limitations belong in
dated evidence, linked from the model and deployment guides.
