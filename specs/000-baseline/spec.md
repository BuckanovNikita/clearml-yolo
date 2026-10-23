# Stage zero: current clearml-yolo specification

Baseline epoch: **2026-10-20**. This document consolidates the pre-reset feature, bug, assessment and dated
maintenance history. It specifies the supported product and preserves evidence limits; it is not an active
implementation ledger. The archival checkpoint and final cutover checks are recorded under [Historical
provenance](#historical-provenance).

## Authority and starting new work

`clearml-yolo` provides native detector training, prediction, validation, evaluation, paired comparison and
reporting through Hydra/hydra-zen applications. Users retain reproducible inputs, exact scientific results,
source identity and verified required ClearML publications. Optional visualization must not determine
computation success.

This baseline replaces retired task-local contracts as current navigation. The [contract
index](../../docs/current-contracts.md) selects the maintained topic guides; those guides remain
authoritative for their detailed operational procedures. [Project
contracts](../../docs/project-contracts.md) summarize cross-cutting behavior. Current code and executed
checks establish implementation evidence; historical plans, task checkboxes and release tags alone do not
establish a physical outcome. An unexplained requirement/code mismatch must be investigated explicitly.

New Spec Kit work starts at **001** in this new epoch, references this specification, and creates its own
specification, plan, architecture record and task ledger. `000-baseline` must not become the active feature
or inherit old unfinished checkboxes. Identify a retired feature using its full historical path and
checkpoint, not its number alone: the old epoch includes two different `003-*` features and both
`037-early-accurate-publication` and `037-cleanup-baseline`. Their artifacts retain separate identities and
are preserved together at H. Existing Git commits, branches and tags retain their meaning. No history is
rewritten.

The [constitution](../../.specify/memory/constitution.md), [agent workflow](../../docs/agent-workflow.md),
installed Spec Kit tooling and current topic guides remain in place. Future tasks follow the native
feature/bug/documentation route, module architecture acceptance, required documentation and authorized
release workflow. This reset does not authorize changes to installed workflow tooling.

## Compatibility and module interfaces

Python support is `>=3.12.13,<3.14`; the development interpreter remains Python 3.12. Package metadata,
lockfile and setup guidance must agree. Optional native packages, drivers and runtimes have additional
platform requirements. On Linux, direct and queued native work requires the actual pidfd/subreaper/`/proc`
capability preflight; an accepted interpreter version alone is insufficient. Changing a queued interpreter
or installation identity requires resubmission. The separate `cy-queue` distribution
uses the `cy_queue` namespace and depends on a compatible CY version. Queue-only
Textual/NVML dependencies and queue tests belong there. Shared process supervision
and lifecycle communication remain in CY, which must not import the queue package.
Install CY from source before the queue in the same environment; neither package
is assumed published on PyPI. See the [extraction feature](../003-portable-training/spec.md).

The package uses `core`, `application`, named `adapters` and `entrypoints`. Core contains pure
project/scientific records and policy. Application workflows use explicit typed `WorkflowDependencies`
supplied per invocation by CLI composition. Adapters own filesystem, process, network, SDK, rendering and
logging effects. No workflow constructs concrete infrastructure or discovers it through global state. Old
Python module paths have no compatibility aliases; regenerate saved Hydra targets using the [import
migration](../../docs/python-import-migration.md).

The [import boundaries](../../docs/import-boundaries.md) and [module
diagram](../../docs/module-architecture.md) own layer, peer, SDK and exact-edge rules. [Executable import
contracts](../../.importlinter) and [architecture tests](../../tests/test_architecture.py) cover exhaustive
placement, cycles, effects, definition-time initialization and static/dynamic composition targets, including
positive and injected-negative cases. Static checks do not prove arbitrary reflection, runtime rebinding,
third-party effects or unrestricted control flow.

Package imports remain inert. First-party Python omits future-annotations imports. Hydra/OmegaConf
conversion stays in entrypoints; protected SDK types do not leak through inner ports. Pandera stage
validation returns copies without coercing, dropping or renumbering source rows; storage owns lexical CSV
conversion and media resolution. [Shared evaluation/reporting](../../docs/shared-evaluation-reporting.md)
keeps scientific computation separate from rendering and publication.

Approved `digital-metrics` and `report-generator` source revisions are maintained in [development
procedures](../../docs/development.md#external-dependencies). Their ignored local source copies and
committed editable lock entries are intentional. Ordinary cleanup does not authorize source edits,
monkeypatches, revision changes or dependency resolution. Frozen compatibility expectations are never
regenerated from the implementation under test.

## Commands and configuration

| Command | Capability |
| --- | --- |
| `cy` | Compose the enabled training, prediction, metrics, comparison and report stages |
| `cy-train` | Train from required CSV ground truth and return prepared input/checkpoint paths |
| `cy-predict` | Produce canonical detection rows and hash-bound prediction provenance |
| `cy-val` | Predict required validation plus requested splits, calibrate and evaluate |
| `cy-metrics` | Evaluate supplied predictions using validation-calibrated frozen thresholds |
| `cy-compare` | Reinfer two independently resolved checkpoints on the current selected split |
| `cy-report` | Generate developer/business reports from the paired comparison manifest |
| `cy-ground-truth` | Convert native annotations into the detection ground-truth table |
| `cy-export` | Export, build or verify a Faster R-CNN deployment bundle |
| `cy-init-config` | Export one selected command wrapper and its required configuration groups |
| `cy-dedup` | Explicit local image-cache reflink deduplication |
| `cy-queue` | Submit, order, execute, inspect, cancel, recover and archive shared jobs |

Execution commands require ClearML and one invocation owner. Initialization, deduplication and queue
help/config inspection do not create an execution task. The [runtime
guide](../../docs/runtime-isolation.md#selected-configuration-export) defines `cy-init-config DIRECTORY
[--command NAME] [--model PRESET] [--force]`: default command `cy`; one selected wrapper; both native groups
for default YOLO model commands; one model preset for another detector; no model group for non-model
commands. Export defaults to Faster R-CNN ResNet-50-FPN. Missing inputs remain `???`. Only selected files
and parents are preflighted. Force replaces regular selected files, never symlink/directory destinations or
unrelated files. Export/help loads no model SDK.

Experiment commands (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-export`, `cy-ground-truth`) check their launch cwd
for Git working-tree membership once before Hydra composition, including help
and configuration inspection. Unverified membership emits an advisory stderr
warning with configuration-versioning guidance and does not change execution or
stdout. CY_HOME and installed source identity are independent. See the
[startup contract](../../docs/runtime-isolation.md#git-workspace-warning) and
[executable checks](../../tests/test_git_workspace.py).

### Native configuration

Default `model=ultralytics` exposes complete top-level `ultralytics` training and `ultralytics_predict`
prediction groups. Native YAML keys are unwrapped at their root; installed upstream defaults, order and
comments are retained. Exported examples put active detection controls first, then commented
project-controlled/inapplicable keys. Commenting examples does not remove their complete composed runtime
schema.

Project training defaults include `yolo11n.pt`, `imgsz=960`, `compile=true`, `nms=true` and `device=null`.
Prediction visibly inherits applicable shared values and defaults to `device=[-1]`, `conf=0.001`, `batch=1`,
`rect=true`, `save=false`. Prediction-local model/project/name are null and do not inherit training routing.
Prediction executes only its resolved group: explicit literals, explicit nulls and values equal to native
defaults retain precedence over inherited values; explicit prediction CLI overrides win over file values.
Native normalization is recorded separately from requested settings rather than rewriting the request.

Known stage-irrelevant keys are excluded from execution and commented in effective YAML. Unknown keys,
non-detection tasks, wrong modes, non-null `embed`, invalid image sizes, raw wrapper `cfg`, non-null native
`cfg`, nested stage-native mappings and duplicate comparison inference-native settings fail validation.
Explicit custom `augmentations` remain supported. Sparse programmatic native mappings must be composed
before use. A produced checkpoint owns pipeline inference; conflicting explicit prediction model selections
fail. Comparison rejects prediction model/project/name overrides in favor of model references and its output
directory.

New detector families use typed `model.train`/`model.predict` settings. Changed controls in inactive YOLO or
native groups fail in both directions; unchanged composed defaults permit mixed-family sweep composition.
Unsupported controls are never silently ignored. ClearML Agent replay restores the selected
backend before runtime initialization; it does not switch an already initialized runtime.

### Configuration resolution and replay

An externally managed ClearML Agent may launch the recorded module entrypoint without
original CLI arguments. Fetch one detached replay snapshot through the ClearML adapter
before mandatory-input validation and backend selection, initialize that backend, then
join the same task through the existing invocation lifecycle. Preserve parameter precedence,
remote script metadata, ownership, required publication, failure reporting and cleanup.
An absent canonical configuration permits complete explicit inputs; malformed or empty
canonical configuration fails. Agent CUDA visibility and native logical devices remain
authoritative. This path requires no queue package, configuration or GPU reservation.


Attached YAML/JSON is resolved against detached command context before sanitization. File roots override
corresponding command roots as whole values; only original file fields are published. Preserve
scalar/collection types, explicit empty/null values, comments and source bytes. Unknown
references/resolvers, cycles, missing mandatory or environment values, unsupported resolver objects and
unresolved active content fail without exposing configuration values. Computed node targets such as
`${${key}}` are rejected; nested resolver arguments remain supported.

Credential provenance follows aliases and the values actually consumed, without reevaluating noncached
resolvers. Keep unredacted executable copies separate from sanitized stored snapshots; credential-bearing
URL signatures are redacted. Noninterpolated inputs retain their original execution paths. Resolved project
copies use explicit invocation scratch, under the current retained-arena filesystem policy. Embedding
callers without an injected resolver must supply concrete documents.

The shared CLI publishes detached resolved JSON `run` after YAML/CLI composition, queue device binding and
supported remote overrides. It contains only selected executable inputs: YOLO retains its native groups and
model backend/preset selectors; other detectors retain `model` settings and omit inactive YOLO groups.
Native-detector dataset format is the effective COCO format. Asset resolution uses an
execution-only copy: canonical selectors, including null defaults, remain intact, while
resolved paths, original URLs and hashes are recorded in a separate `model_assets`
Configuration Object, outside canonical replay/cache inputs. Later result provenance cannot replace frozen
executable roots; native normalization remains separate. Consumed `dataset` and explicit `report` remain
separate Configuration Objects; `model_assets` stores resolved non-YOLO asset provenance
as an `assets` list of original URLs, paths, hashes, overrides and revisions.
Configuration copies are not artifacts. Embedding callers still own complete
executable input recording through the invocation/tracking interface. Result-only sections, including
`evaluation_result`, `fiftyone_result` and `export_result`, never replace executable inputs. SDK proxy
containers are detached; inherited SDK connection flags do not own execution.

Sanitized deterministic JSON `run_overrides` contains recursive differences from built-in project defaults
for the same command and selected preset, independently of user YAML/search-path shadowing. Preserve
meaningful false, zero, null, explicit empty collections, value types and list order; prune unchanged values
and empty parents created by pruning. Exclude output routing, tracking destinations/tags, result provenance
and inactive groups. The view is informational: execution and cloning use `run`, never `run_overrides`.

### Stable experiment parameters and controller caching

Native `General` excludes `device`, `project`, `name`, `save_dir`, `exist_ok` and CSV-owned generated
`data`; all remaining scientific arguments retain their meaning.
`clearml_yolo.adapters.clearml.parameters.project_native_parameters` returns a detached projection; the
session boundary adds sanitization. Owner callbacks, DDP replay and native-detector publication share this
policy. Filtering new connection inputs does not delete parameters inherited from historical templates.

Training publishes sanitized validated General before dataset preparation, after supported remote overrides.
Native owner callbacks may subsequently refresh observed normalization, including DDP and alternative
detectors. Existing execution-only exclusions remain. Commands that skip training do not create training
parameters. Remote scientific override reads do not publish unvalidated input or treat a redacted
observation as executable credential material. Embedded workflows use the typed tracking port for early
General and retain responsibility for recording their complete executable run.

New canonical run snapshots are JSON with literal Unicode (`ensure_ascii=False`); historical HOCON remains
replayable. YOLO remote training restores full native settings from `run.ultralytics` and applies scientific
General overrides. Legacy absent-run or missing-native-group replay restores execution settings from old
General before writing a full snapshot. A present group, including an empty mapping, remains authoritative.
Current explicit routes and invocation identity own output destinations; old owner-derived routes never
override them. New detectors replay `run.model`; observed General does not override their executable
settings.

The opt-in controller API `clearml_yolo.adapters.clearml.cache.normalize_task_hash(representation: dict[str,
Any])` returns a detached representation for `ClearmlJob.register_hashing_callback`. Import/call performs no
SDK, filesystem, network or registration operation. Register before cached jobs are created; compose any
existing callback explicitly. Only canonical execution-module scripts are normalized. Preserve SDK-supplied
code/container identity, unknown fields/configurations and scientific inputs; inject an explicit
normalization-policy version.

Normalize accepted explicit CUDA ordinals to device type/count only in known native, General and inference
contexts. CPU/MPS, unresolved/invalid selections and different device counts stay distinct. Selector grammar
follows each consumer; typed detectors and export cannot inherit YOLO's permissive forms. Unsupported
document syntax, malformed markers and ambiguous SDK/JSON escape semantics preserve executable identity
instead of creating collisions. For a recognized clearml-yolo execution script, the derived `run_overrides`
object is always excluded from cache identity, including conservative fallback and an already-versioned
representation. Unknown scripts remain untouched. No other unsupported content is normalized by this
exception. Historical HOCON is not reinterpreted.

`PreparedDataset.cache_identity` carries the existing preparation key. When present, training records
`run.prepared_dataset={cache_identity, root}`. Only proven generated paths under that root normalize to
identity plus relative path; unrelated sources, checkpoint paths, formats, vocabulary and split definitions
remain significant. Drop only enumerated output-routing/provenance fields, never generic `name`, `path` or
arbitrary `*_result` keys. Keep ClearML project when it selects unresolved models, and pipeline run roots
when skipped stages consume existing outputs. Controllers should freeze task IDs and immutable inputs before
lookup. A hit reuses remote outputs and creates no new local output. Controller overrides use JSON text. See
the [controller recipe](../../TECH_DETAILS.md#clearml-pipeline-cache-identity).

## Detection inputs, dataset cache and output routing

[Input provenance](../../docs/input-provenance.md) governs lexical detection tables: literal `NA`, `NULL`,
`nan`, `None`, numeric-looking and Unicode identities survive; empty background cells remain empty; row
order and round-trip numeric precision survive. Relative media paths resolve against the source CSV,
including after Hydra cwd changes. Original export rows retain lexical source values. Evaluation requires
canonical `image_name=name` and known image membership; raw `stem`/`path` exports remain available but
cannot silently enter scoring. New sidecars bind naming mode to prediction bytes; historical missing modes
require canonical membership.

CSV ground truth is mandatory for training; native dataset paths cannot substitute. YOLO supports
`dataset_format=ndjson` (default) and `flat`; native detectors derive COCO. Train/validation populations
must be nonempty, and enabled stages require their splits. Training drops invalid boxes with a visible
count, excludes background rows from that count, and fails if no valid training boxes remain. Cleaned ground
truth feeds later stages. CSV preparation owns native data/filter/class remapping, records overrides and
rejects native resume. Source images remain immutable.

YOLO annotation conversion uses native EXIF-aware dimensions, including JPEG orientations 6/8. Source
normalized coordinates must be finite within `[-0.01,1.01]`, with positive box sizes; invalid labels fail
with file/line context. Valid edge-crossing boxes clip. NDJSON preserves original filename casing; flat
exports retain numbered names. Prepared outputs include cleaned ground truth, data reference, format, class
mapping, manifest and local conversion diagnostics; returned paths must actually exist.

Cache identity binds CSV bytes, resolved media-reference identity, format and preparation version. Equal
absolute references can reuse across CSV locations; different resolved images cannot collide. Hits avoid
image-content hashing, mtime checks, copying and conversion. Changed source bytes at unchanged image paths
require explicit idle invalidation. Consumers hold native locks; unsupported locks fail without soft
fallback. Invalid/incomplete entries remain for deliberate inspection, never automatic deletion.

The [filesystem policy](../../docs/filesystem-policy.md) owns project containment and SDK defaults.
`CY_HOME` defaults to launch cwd; relative selection resolves before Hydra. Project outputs, datasets, logs
and scratch must resolve beneath it, including symlinks. External inputs and normal SDK selectors/caches
remain valid. Explicit shared queue metadata/coordination are separate exceptions. No startup recovery scan,
recursive scratch deletion, SDK constant substitution or persistent settings rewrite is allowed.

`run_dir` owns pipeline routing: conflicting stage destinations and native project/name fail. Pipeline
layout retains `detect/train`, `native/predict`, `predictions.csv`, `metrics`, `comparison` and `reports`.
Standalone producers create fresh task-derived destinations and require explicit inputs; explicit
`run_id`/allowed destinations retain their semantics. Encoded project/task/task-ID components prevent path
ambiguity, including Windows reserved names and `latest`. Logical split names remain unchanged;
filename/artifact components percent-encode unsafe UTF-8, separators, percent and dots.

### Explicit cache deduplication

`cy-dedup [DIRECTORY] [--dry-run]` defaults to `CY_HOME/.cache` or launch cwd `.cache`. It requires an
existing directory, scans regular image files recursively without following symlinks, and matches exact
case-sensitive filenames plus identical bytes (size, streamed SHA-256, byte comparison). Supported suffixes
are `.bmp`, `.dng`, `.jpeg`, `.jpg`, `.mpo`, `.png`, `.tif`, `.tiff`, `.webp`, `.pfm`, `.heic`,
case-insensitively; files are not decoded.

Deterministic same-device duplicates use Linux FICLONE through an atomic temporary sibling. Preserve
ownership, mode, atime/mtime and xattrs; inode/ctime/birth time may change and reads may change atime.
Hardlinks, cross-device files and unsupported reflinks/platforms are skips, without hardlink/copy fallback.
Changed files prevent replacement. Unexpected I/O fails after reporting any earlier successful replacements;
owned temporary files are cleaned. Use an idle cache. Dry-run changes nothing and does not probe support.
Counts are scanned/duplicates/reflinked/skipped/failures, not measured reclaimed bytes. Exit 0 includes
skips; 1 is operational failure; 2 is usage/invalid root.

## Detector backends and deployment export

The [model guide](../../docs/multi-model-backends.md) owns native prerequisites, pretrained sources and
limitations. Supported selections are DEIMv2 S/M/L/X; RF-DETR Nano/Small/Medium/Large; Faster R-CNN
ResNet50-FPN, ResNet101-FPN, ConvNeXt-Tiny, Swin-Tiny, DINOv2-Small and DINOv3-Small; default YOLO remains
supported. Lazy composition reports the selected missing prerequisite without initializing another backend.
Typed controls, exact foreground strings, empty images and coordinate/membership semantics survive native
dataset conversion. Background detector slots are not public labels.

The [asset contract](../../docs/model-assets.md) covers DEIMv2, RF-DETR and every
Faster R-CNN preset. Explicit local paths remain authoritative and missing explicit
inputs fail. Training resolves matching pretrained assets only when requested and
not superseded by explicit full detector weights. Backend adapters preserve native
loading transformations; no full-detector or random-weight substitution for a
requested backbone. Ultralytics defaults, downloads and dependencies are unchanged.

Resolution occurs only during execution: valid local/cache content, configured proxy,
then upstream. Empty/unset proxy variables select upstream; non-GitHub hosts retain
their original endpoints. GHR preserves the complete GitHub release path beneath its
repository root. GH derives the Artifactory downloadCommit request for the approved
DEIM revision. Managed source extraction checks safe archive entries and a packaged
approved-revision code/configuration manifest; explicit checkouts retain validation.

Managed weights use `CY_HOME/.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>`,
with identity derived from canonical source, revision and available checksum. DEIM
uses `CY_HOME/.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz` and adjacent
`<revision>/`. Reuse valid library caches without global SDK changes. Outer adapters
own bounded HTTP/retries, per-asset locking, temporary downloads, atomic publication
and integrity validation with standard authentication/TLS. Errors list every known
missing asset's original full URL, exact absolute destination, override and access
requirements; attempted proxy credentials are redacted. Manual placement works
without a receipt from an earlier online download. Dependencies remain externally managed.

Owned checkpoints embed backend, preset, foreground vocabulary, preprocessing and source/dependency
identity; external descriptors add the checkpoint SHA-256. Validate descriptors, sidecars and available
remote hashes before inference. Complete native `ModelRef` assertions may identify raw local or
task-recovered checkpoints but cannot override conflicting embedded metadata. Partial assertions do not
relax validation. Same-byte references must agree on resolved model metadata, although display labels and
thresholds may differ. Independent mixed-family comparison retains one current inference/evaluation request,
with effective preprocessing recorded.

The [TensorRT guide](../../docs/tensorrt-deployment.md) governs `cy-export`. ONNX generation uses CPU/FP32;
build/verify select a GPU and FP32 or FP16. Each operation owns one task, publishes its produced
graph/engine/metadata or verification/corpus, and creates no trained Output Model. Sidecars bind checkpoint,
graph and engine hashes, vocabulary, preprocessing, inference policy, precision, runtime/plugins and
profiles. Build consumes the ONNX sidecar; verify binds engine, native checkpoint and fixed labeled corpus.
Settings remain under `export`, results under `export_result`. Default workspace is 4 GiB; it is not an
inference-memory promise.

`DetectorExporter.execute(request, destination, *, artifact_ready=None)` accepts an optional typed
`Callable[[str, Path], None]`. Export producers announce finalized immutable graph, engine, metadata and
corpus files immediately; the application uploads them and verifies the returned inventory without duplicate
upload. The final verification report publishes only after all cases/corpus checks finish; intermediate
reports remain local. A complete report that fails its quality gate uploads before the task fails.
Callback/upload errors propagate, earlier complete artifacts survive later producer failure, and export
adapters acquire no ClearML dependency. Final upload verification remains mandatory.

Dynamic NCHW profiles have batches min/opt/max 1/2/4: full-frame width×height 960×608 / 960×608 / 960×736;
strips 1536×128 / 1920×256 / 1920×256. Batches 1–4 and interior shapes must fit one whole profile with valid
canvas/image sizes. Reject cross-profile/out-of-profile requests. Proposal processing, ROI and NMS remain
in-engine. Explicit counts exclude padded detections; zero results are valid. Preserve normalization,
resize/padding, DINO patch behavior and native coordinate restoration. The standalone runner requires
TensorRT/CUDA and ordinary array/image utilities, without Torch or ClearML; it owns no tracking task or
scheduling policy.

FP16 uses the guide's strong tensor-type policy: eligible backbone products have Half operands/products with
private Float accumulation; heads, geometry, attention and identified combined QKV projections remain Float;
TF32 is disabled. Unsupported projection/layout/initializer forms fail before mutation. Source graph bytes
and external tensor contracts remain unchanged.

Each preset/precision acceptance binds identical checkpoint, source-byte corpus, class mapping,
preprocessing and actual evaluator. Test data is disjoint and frozen after validation-based selection; do
not tune on test outcomes. Exercise endpoints, interior/profile transitions, batches, empty/crowded cases,
rejection, fresh Torch-free execution, tensor/detection parity and finite outputs. Maximum absolute mAP50–95
loss: 0.001 FP32 and 0.005 FP16; report per-class recall and actual latency/memory. TensorRT 10.13.0 is the
CUDA 11.8 target, requiring its own runtime/GPU rebuild and acceptance. Local newer-CUDA evidence does not
prove target or binary portability.

## Evaluation, comparison and historical model recovery

Calibrate candidate confidence thresholds on `val` once; freeze them for selected train/test evaluation and
comparison. Defaults for `cy`, `cy-val`, `cy-metrics` are train/val/test; preserve explicit subsets and fail
missing requested splits. Pipeline comparison uses test; standalone comparison defaults to test and accepts
another current split. Reports consume the new paired manifest's split and dashboards. Historical
predictions/metrics/configuration never replace current comparison inputs.

Prediction geometry is filtered only in an in-memory evaluation copy before preprocessing, calibration and
AP: missing, nonnumeric, nonfinite, reversed, then zero-area reasons are mutually exclusive. Warn once per
frame with counts and up to five image names. Raw CSVs remain intact; all-invalid predictions score as empty
and produce unmatched-GT false negatives. Schema/confidence failures remain fatal. Geometry-valid raw AP
predictions include valid low-confidence/NMS-suppressed boxes; fixed-threshold matching uses its prepared
population and matching indices.

Matching supports `greedy`, `hungarian`, `iou_prior`; AP integration supports `interp`, `continuous`. IoU
and false-discovery `q` are finite within `[0,1]`. Exact validation and prepared GT deduplication remain
application policy. Scientific adapters use the approved public `digital-metrics` computation, including
confidence ordering, ties, float precision and unavailable values; they do not rematch rendered reports.
Paired statistics use shared eligible classes and the split-wide BH family, with pooled tests outside it.
Rendering does not choose the protocol.

Automatic baseline selection is the latest completed prod-tagged task, excluding the current task. All
ordinary requested tags must match and task-name regexes match the entire name. Missing automatic baseline
records a skip and keeps candidate results; invalid explicit references fail. Local references require
weights and exact thresholds. Task references recover weights and thresholds once, yielding one coherent
provenance.

Explicit threshold maps win. Otherwise use the first present source in this order:
`metrics_best_confidences_val`, `best_confidences_val`, `metrics_best_confidences_test`,
`best_confidences_test`, `metrics_dashboard_full_val`, `dashboard_full_val`, `metrics_dashboard_full_test`,
`dashboard_full_test`. Named payloads accept JSON mappings, Series/DataFrames and downloaded CSV/CSV.GZ;
dashboards accept frames or CSV/CSV.GZ/XLSX with `confidence`. Preserve exact string class names and
available precision. Empty/duplicate classes, unsupported shapes, missing/nonfinite/out-of-range confidence
or a present undownloadable source fail strictly without trying a later source. Dashboard fallback warns
about rounding and unavailable calibration provenance; it never claims original full precision.

When Output Models exist, select unique metadata-marked best, else unique decoded
`best.pt`/`best.pth`/`best.ckpt`, else the last registered model with a warning. Ambiguity or selected
download failure fails; do not download other models or use artifacts while any Output Model exists. Without
models, try artifacts in order: `train_weights_best.pt`, `.pth`, `.ckpt`, `train_weights_best`, `best.pt`,
`.pth`, `.ckpt`, `best`, `model`, `checkpoint`, then remaining recognized checkpoint suffixes
lexicographically. Download only the selected existing source and validate it. Unasserted `.pth`/`.ckpt` and
direct model-URI recovery require embedded detector metadata.

Recovered weights retain source task/model or task/artifact provenance; never invent model links for
artifacts. Validate available identity/hash/descriptor associations. Original architecture loading is not
guaranteed by recovery; loading errors remain actionable. Current publication stays one verified best Output
Model and one exact validation threshold CSV; recovery never rewrites source tasks.

## Required publication and task lifecycle

One invocation owns exactly one ClearML task; nested stages reuse it. Native/DDP workers neither create
tasks nor upload. Register expected publications before finalization. Publish validated effective ground
truth immediately after its canonical file is complete. Workflows declare all enabled prediction-result
contributors before registering rows and explicitly complete each after its final mutation. The last
completion assembles/uploads one complete `predicts_csv` before later comparison statistics, reports or
optional publication. Finalization verifies contributor completion and all required upload/model/flush
barriers; it never publishes an incomplete aggregate. A later failure preserves earlier complete uploads and
local incomplete shards. Missing output, callback, journal, computation, upload, readback, flush or
interruption errors fail task and command while retaining local output. Required owner finalization has the
current ten-minute main-thread Unix deadline. Do not replace an original computation exception with
cleanup/finalization errors.

New local tasks publish canonical module entrypoint and repository-relative working directory.
Source-checkout discovery uses imported code, including worktrees, to record sanitized origin, branch and
exact HEAD; detached branch is `HEAD`. Verify SDK readback before work. No raw arguments or uncommitted diff
is uploaded; recorded HEAD does not claim to include local edits. Remote Agent script metadata is preserved.
Missing Git/source/origin warns and leaves fields unavailable; installed wheels never adopt an unrelated
enclosing checkout. Historical tasks are not backfilled.

### Publication inventory

| Artifact or destination | Required current contents |
| --- | --- |
| Output Models | One owned best checkpoint, verified association, bytes and metadata |
| Native Scalars/Plots/Debug Samples | Owner training/validation telemetry and permitted previews; no native validation PR images |
| `gt_csv` | Effective ground truth once per invocation with original lineage |
| `predicts_csv` | One combined prediction/evaluation context table, including valid empty results |
| `metrics_best_confidences_val` | Full-precision validation calibration when performed |
| `metrics_dashboard_full_SPLIT`, `metrics_dashboard_dtrk_SPLIT` | Original full/DTRK workbooks per evaluated split |
| `comparison_ROLE_dashboard_full_SPLIT`, `comparison_ROLE_dashboard_dtrk_SPLIT` | Candidate/baseline current reinference dashboards |
| `compare_workbook_SPLIT`, `compare_workbook_SPLIT_excluded` | Paired XLSX retaining `Сравнение`; excluded-class CSV |
| `report_dev_SPLIT`, `report_business_SPLIT` | Final paired developer/business XLSX |
| `export_onnx`, `export_engine`, `export_metadata` | Operation-produced deployment artifact and metadata |
| `export_verification`, `export_corpus` | Verification report and fixed-corpus manifest |
| Configuration Objects | Active executable `run`, informational `run_overrides`, resolved asset provenance `model_assets`, consumed dataset, explicit report and meaningful provenance |
| General | Sanitized scientific native arguments |

Ground-truth/train register GT; train also owns model/telemetry. Predict adds not-evaluated rows.
Metrics/val add evaluated contexts, calibration when needed, dashboards and current-model plots. Compare
adds separate reinference contexts, candidate/baseline dashboards and paired outputs when a baseline exists.
Report publishes its final workbooks. Pipeline publishes the enabled union with CSVs once. No automatic
baseline means candidate outputs plus a skip reason, not fabricated pairs.

Prepared data/NDJSON/COCO, archives, descriptor sidecars, native YAML, raw metrics,
match/threshold/methodology tables, duplicate evaluation summaries, JSON/PNG diagnostics, comparison
manifests, input workbooks and publication receipts remain local. Do not add config or duplicate checkpoint
artifacts. Content deduplication still satisfies each logical expectation. Confidence plots must be freshly
generated; clear only recognized current/legacy names, preserving unrelated/sibling outputs.

Exact validation thresholds upload after calibration and final CSV writing. Each model/split dashboard
uploads after final identity annotation, before the next evaluation or comparison statistics. Comparison and
report workbooks upload after their final annotations. Ground-truth repeat registration is a no-op only for
identical effective truth; conflicting truth fails. Existing canonical artifact names remain unchanged and
no intermediate replacement uploads are introduced. Best Output Model publication still follows finalized
checkpoint selection and retains its native ownership and download/metadata verification.

### Canonical result rows

`TrackingSession` provides `publish_training_parameters(task, values)`, `declare_result_producers(task,
producers, *, output_dir)` and `complete_result_producer(task, producer)`, where `ResultProducer` is
`Literal["predict", "metrics", "compare"]`. Pipeline declares the full enabled set; standalone stages
declare their own producer, and standalone validation declares prediction plus metrics. Identical or
active-subset declarations are allowed; duplicate/unknown producer declarations, undeclared/duplicate
completion, expansion of the declared set and row mutation after all producers complete fail. A skipped
comparison completes explicitly without fabricated rows; an empty producer set requires no predictions
artifact. Alternative injected tracking implementations must provide these typed operations.

Durable invocation shards retain original fields and source identities assigned before preprocessing.
`row_type` is `gt` or `predict`; `source_row_id`/`object_id` distinguish identical boxes and repeated
indices; context/model/split scopes identify each result. Statuses are `not_evaluated`, `background`,
`excluded`, `TP`, `FP`, `FN`, `filtered`. Retain geometry failures, duplicate GT and
preprocessing/confidence/class exclusions. Unselected prediction images remain `unassigned` with
`outside_selected_splits`; they never expand the authoritative scoring population.

`confidence_threshold` and nullable `is_below_threshold` use strict `<`; equality stays. JSON
pre/post-threshold relationships retain match ID, phase/status, nullable source endpoints, prepared indices,
labels, confidence and IoU at both available endpoints. Map prepared indices explicitly to original source
IDs; never join by box coordinates. Prediction-only rows cannot acquire invented thresholds, matches or
evaluation. Combined exports include calibration/requested contexts and other represented prediction splits,
without inventing contexts for unused GT-only splits.

### Model verification and source identity

YOLO callbacks register the best model; absence must not create a wrapper fallback. Native-detector owner
publishers register their single descriptor-bound model directly. Asynchronous upload waits/flush alone are
insufficient: reload, require unique best association, reject transient/failed URLs, force-download nonempty
bytes and compare SHA-256. Enrich the same model and verify fresh readback without a second weight upload.
Metadata records real architecture, vocabulary, task/project, role, source identity, available package
versions and known lineage; never fabricate IDs/timestamps/production tags.

Exact project-local name collisions include archived records and exclude current IDs. Unused names stay
unchanged; bounded rechecked readable suffixes are shared between task and owned model without changing
paths/URLs/IDs. Clones resolve their own names. Local checkpoint identity sidecars bind the finalized model
name/original training task to checkpoint bytes; prediction sidecars additionally bind prediction bytes.
Stale, malformed or contradictory identity fails. Reporting task IDs never substitute for source training
task IDs.

Only the invocation-owned verified best model may receive exact validation thresholds, after
prediction-checkpoint hash association and full remote readback:

| Metadata key | Value | SDK type |
| --- | --- | --- |
| `clearml_yolo_confidence_thresholds` | Exact float JSON | `str` |
| `clearml_yolo_confidence_threshold/<class_name>` | Each `repr(float)` threshold | `float` |
| `clearml_yolo_calibration_split` | `val` | `str` |
| `clearml_yolo_calibration_checkpoint_sha256` | Prediction checkpoint SHA-256 | `str` |

Verify unchanged model ID, task, project, URL and downloaded hash, plus exact metadata value/type
readback, and extend the original completion barrier with these expectations. Standalone metrics never
creates or mutates models. The exact threshold CSV remains required.

## Reports and readable visualization

The [readable-output guide](../../docs/readable-output.md) governs human text across CLI/TUI, diagnostics,
consoles, workbooks and plots. Readable names/roles and distinct aliases replace opaque identifiers in
visible labels. Exact IDs/hashes remain in machine provenance, explicit JSON where permitted, hidden
identity, raw captures and link targets. Formatting cannot change source bytes, metric values or
acknowledgements.

Each current-model split has one `Confusion matrix` chart selecting Counts, Row %, Column %, Overall % from
identical post-threshold integer counts. Counts is initially visible and exactly one heatmap remains
visible after selection. Percentage views share a fixed 0–100 scale; hover retains the original integer
count and applicable denominator. True rows/predicted columns preserve class order/background; zero
denominators show finite zero and `no observations`. One test-only `Precision-recall` chart combines all
classes at IoU .50 from the authoritative geometry-valid AP population, preserving ordering/ties, AP method
and confidence/cumulative TP/FP hover. GT without predictions has AP50 zero; absent GT has unavailable
recall/AP. Null-gap legend traces do not invent observations. No baseline charts or comparison tables appear
in Plots; baseline rows/dashboards, paired reports and headline values remain. Filter native validation PR
callbacks only within owner scope and restore state, including DDP owner replay.

Visible series use model name and split. Repeated checkpoint/split publication reuses its invocation slot;
model/context fallback and readable stage/ordinal suffixes separate collisions. Numeric/Unicode labels
remain distinct. Stored source identity wins over custom fallback labels. Unknown local sources require
`model_label`, comparison reference labels, or legacy report baseline/candidate labels as applicable; these
provide names without inventing training tasks or registering models.

Every new workbook sheet carries literal readable model banners, paired roles and recorded/unavailable
training-source status. Preserve original values, formulas, styles, merges, filters, panes and print
semantics; repeat banners on printed pages and fit width to one page. Annotated workbook readers recover the
embedded original layout only after fingerprint validation; edited/resaved decorated workbooks fail
ingestion. Historical unannotated workbooks remain readable. Rendering never changes pinned libraries or
historical remote artifacts.

Developer/business/statistical reports preserve one-sided classes: measured values stay, absent
operands/comparisons are `NA`, never synthetic zero. Each model's averages and business inputs use its own
eligible population; differences/statistical tests use the shared eligible population. Untestable rows do
not enter BH or significance verdicts. Empty shared populations still show available model metrics with
unavailable pooled comparisons. Exact text labels survive, including `0001` and literal `NA`; numeric
threshold footer cells are not classes. Aggregate availability appears below metric tables as
`<metric>-valid-class-count` (`AP50`, `AP75`, `AP50-95`), retaining finite-zero counts, `0/N` and `0/0`.
Apply this layout before identity annotation.

## Optional FiftyOne publication

The typed publisher boundary exposes enabled/preflight/publication without SDK objects in requests/results.
Disabled publication imports no FiftyOne. Enabled operations use fresh bounded workers under the [runtime
guide](../../docs/runtime-isolation.md); defaults are 60/900/30 seconds for preflight/publication/lock
acquisition, all finite positive. Workers have no GPU visibility, reservation or ClearML ownership. Success
requires zero exit, matching operation/task and complete receipt. Factory/preflight/
request/publication/receipt/link errors warn without failing successful computation; interruptions retain
normal semantics. Partial state remains for same-task retry.

One sample per image retains raw predictions separately from evaluated fields, task-hash namespaces and
exact source lineage. Finite ordered zero-area predictions from clipping remain raw evidence;
reversed/nonfinite boxes or confidence outside `[0,1]` fail; labelled GT requires positive geometry.
Effective GT identity hashes the bytes actually parsed. A local receipt records completion markers, payload
paths, semantic field mapping, per-split evaluation keys and aware UTC publication time; canonical run
stores its meaningful link, not another receipt artifact.

One persisted detection evaluation per task/split uses `digital_metrics`, exact source matches and existing
claimed-GT confusion rules without rematching. Native evaluated predictions exclude `filtered` boxes; the
complete audit overlay retains them without native evaluated status. Persisted IDs support loading,
reporting, confusion, patches, rename and delete; same-task retry preserves other tasks. Optional schema-v1
reports carry original confusion/PR50/AP50/AP75/AP50_95; absent reports remain unavailable. mAP is mean
AP50_95 over classes with GT; mAR and restricted-subset AP/PR are unavailable. Subset fixed-threshold arrays
restore on exit.

The `@clearml-yolo/evaluation` App extension is explicitly installed in the matching server/backend
environment; publication does not install it or migrate old runs. Native evaluations appear for old data
only through new publication/reruns. Normal SDK settings discovery remains intact; invalid optional SDK
configuration uses the warning/no-op boundary instead of blocking help or substituting project defaults.

## Direct execution, shared queue and diagnostics

[Queue operations](../../docs/queue.md) and [lifecycle diagrams](../../docs/queue-lifecycles.md) are the
current execution authority. Direct commands pass configured native devices without project GPU
discovery/waiting/reservations; direct multirun is sequential BasicLauncher. Old `queue.*`, `autogpu.*`,
`auto_gpu.*`, queue roots/launcher and force controls fail with migration guidance, not silent translation.

The separate queue accepts `submit --command {pipeline,train}`, defaulting to pipeline,
and launches the corresponding existing CY entrypoint. Queue submissions freeze complete
sweeps, input settings, both packages' installation identities, interpreter, owner and resource
requests. Configuration locations, coordination namespaces, lock identities, durable
records/history, ownership, cancellation/recovery and acknowledged handoff remain
compatible. Upgrades stop all participants together, preserve records and resubmit
pending work after environment changes; see the [offline upgrade](../../docs/queue.md#coordinated-package-upgrade). Owner workers execute only their UID's jobs; collaborators may reorder pending jobs through
revision-checked public operations. Per-host earliest runnable ordering and whole-allocation claims apply
across roots. CPU phases remain CPU; inference retains the first allocated device. Used VRAM must be
strictly below 2048 MiB immediately before launch; unknown required telemetry, visible MIG or damaged
coordination fail closed. The fixed cutoff is not a promise the workload fits.

Every effective MULTIRUN, including one-job sweeps, receives one fresh shared
`multirun-YYYYMMDD-HHMMSS-<six-word-phrase>` UTC tag. Explicit user tags survive; ordinary RUN adds none.
Queue snapshots freeze the group; remote replay retains the attached task metadata rather than starting a
new grouping policy.

Each user supplies XDG/default or explicit absolute `CY_QUEUE_CONFIG` TOML with queue name, absolute
metadata root and coordination root. No merging, storage defaults or automatic creation of settings. Host
binding enforces one coordination location. Eligible NFS/NFSv4 coordination requires effective hard mounts
and local flock, with the guide's rejected options and fail-closed mountinfo parsing. Private snapshots, UID
boundaries, shared host PID/lock namespaces and cooperating-user assumptions remain. Actual NFS operation
requires separate evidence from simulated eligibility checks.

External guardians own queued descendants and locks outside ClearML finalization. Training-finished
notification follows native return/memory release; durable contraction keeps the first GPU and releases
extras before acknowledgment. Missing notification retains all; lost acknowledgment stops inference and
never restores released extras. Worker death does not free live allocations. Owner cancellation has bounded
grace before identity-proven TERM/KILL cleanup; repeated signals do not reset deadlines. Unknown ownership
remains recovery-required, without retroactively failing a successful completed ClearML task. Stale unlocked
metadata alone does not veto admission.

Physical-index `gpu disable/enable/free/release` and generation fencing follow the guide: free/release
clears only that device's existing holds/claims across roots, without tokens, reasons, force flags,
memory/process checks, signals or outcome changes. Sibling reservations survive; older guardians cannot
recreate claims or affect newer generations. Every future launch still needs fresh memory admission.

Stable `job-N` numbers survive reorder/archive/restart. Owner-only archive/restore changes visibility for
terminal jobs without deleting history or changing state; recovery-required jobs remain visible. A private
per-job refresh failure retains its public summary and warns without hiding healthy jobs or mutating
lifecycle/reservations. Shared manifest/configuration/coordination failures remain queue-wide errors.

The [diagnostics guide](../../docs/diagnostics.md) owns redacted caught-error context, DEBUG location-only
stacks, TRACE operations/heartbeats/thread snapshots and preserved caller sinks. FD capture retains original
Python/native/DDP stdout/stderr; an independent terminal mirror and attach-only publisher serve the existing
owner task. Required console/scalars use bounded batching/final-offset barriers, with no automatic replay of
uncertain delivery. Prediction suppresses native verbosity and uses one rate-limited progress indicator.
`command.return` follows cleanup and is not a success assertion.

## Verification and delivery requirements

Each new task records affected modules/interfaces/effect owners, executable contract coverage and acceptance
commands before implementation. Reconcile the actual owned diff after integration and checks; substantive
work requires fresh independent review. Documentation and portable usage guidance are part of acceptance.
Missing/failing required checks remain gaps. Historical waivers apply only to their specified targets.

Use [development checks](../../docs/development.md#verification) and [static-analysis
policy](../../docs/static-analysis.md): affected/full pytest as appropriate, Ruff, strict mypy, Vulture,
separate import contracts and architecture tests, Markdown/link checking and required hooks. Ruff rules live
in `ruff.toml`, import contracts in `.importlinter`; `pyproject.toml` keeps package/small tool settings.
Advisory unused-code findings need callsite/dynamic-consumer/contract evidence before deletion.
Documentation checker tests include negative cases; its parser does not validate external links, command
semantics, arbitrary runtime Markdown or Mermaid grammar.

Frozen tests protect scientific values, signatures/defaults, configuration/CLI, workbook semantics and
byte-exact original-content recovery. Mocked payloads prove adapter behavior, not native/GPU/server results.
Native acceptance follows the [end-to-end skill](../../.agents/skills/running-end-to-end-tests/SKILL.md):
actual execution, required readback/download, checkpoint/provenance validation, paired current-image
comparison and owned-resource cleanup. Releases verify the source checkout. Project `.whl` and `.tar.gz`
distributions are built only for concrete debugging work; any diagnostic packaging claims require
appropriate isolated installs, with reused dependencies stated.

### Local release interface

The [commit/release procedure](../../docs/development.md#commit-procedure) owns hooks and exact preservation
of local `[tool.uv.sources]` around every commit attempt. Stage only authorized changes, preserve other work
and inspect generated changelog changes; do not bypass hooks, reset or stash to obtain acceptance.
`scripts/local_release.py --changelog` regenerates English history from committed Conventional Commits
without staging; changed output requires review/retry. Shallow history is rejected without automatic fetch;
detached refresh is skipped.

`scripts/local_release.py --install-hooks` installs owned pre/post-commit hooks and refuses unrelated custom
post-commit replacement. Normal/manual release runs on master only: fix/perf patch, feat minor, breaking
minor below 1.0, nonrelease types alone no version. It includes unreleased reachable history, creates a
checked version commit and annotated `vX.Y.Z`, and edits only root version tokens/changelog plus private Git
recovery metadata; no dependency resolution or automatic push/fetch/build occurs. Concurrency, dirty
source/index, inconsistent metadata/tag or changed prepared recovery content fail/defer explicitly;
post-commit failure does not undo the contributor commit. Recovery validates recorded identities/hashes and
never rewrites existing refs. Legacy recovery records without a changelog checksum cannot tag automatically.
Exit 0 means release complete or an explained skip; exit 1 means a reported failure/defer, with the original
contributor commit retained. Authorized delivery explicitly pushes and verifies branch/tag refs. Publish
Git commits and annotated tags only. Project `.whl` wheels and `.tar.gz` source archives are debugging
tools, never release deliverables or routine release checks. GitHub Release objects, assets, registries
and deployment require separate scope.

## Historical evidence and limits

The pre-reset release at integration start is v0.34.1. During cleanup integration, origin advanced to
v0.35.0; its source/evidence commits were merged normally and preserved below before archival
cutover. Upstream delivery does not certify the cleanup's newly merged source or erase task-specific
verification gaps. New cutover delivery is recorded below only after actual checks. Older status text such
as “approved” or unchecked tasks may predate later review/release evidence; use the complete dated chain at
checkpoint H.

| Historical area | Preserved outcome and limit |
| --- | --- |
| Native detector/export feature 025 | v0.24.0 records all advertised presets and FP32/FP16 local matrices. Relative export quality uses a frozen small single-class corpus, not general accuracy. Current QKV policy combines fresh transformer runs with exact lowered-graph equivalence for accepted CNN engines. CUDA 11.8 target execution/binary portability remain unverified. |
| Shared extraction 028 | Frozen offline science/workbook/API compatibility and independent review passed. No new accuracy, native GPU or server-upload claim follows. |
| Shared queue 029 and supervision 031 | Software and scoped CPU/single-GPU evidence exist; five-physical-GPU, associated multi-GPU/NCCL/cancellation and actual two-user/two-host NFS obligations were closed by explicit user waiver on 2026-10-16. Their physical outcomes remain unverified. |
| Historical native failures | Original cuBLAS, intermittent CPU-DDP SIGILL and ClearML missing-model-ID evidence remains unresolved; later passing scoped runs and the waiver do not establish their causes or fixes. |
| Readability/archive 034 | v0.33.0 includes actual separate-user ownership/workers and CPU/single-GPU publication/download. GPU facts in the multiuser tests were synthetic; physical multi-GPU, two-host NFS and browser interaction were not exercised. |
| User configuration/NFS eligibility 035 | v0.34.0 verifies discovery, mountinfo validation, software and isolated package behavior. Actual NFS locking, reconnect, server restart/outage and multi-host execution were not run. |
| Queue refresh isolation | v0.34.1 verifies reproduced missing/malformed snapshot isolation and headless rendering. Exact original historical ValueError, physical GPU, NFS outage and live ClearML behavior are not established by those checks. |
| Static configuration split 026 amendment | Local checks, semantic import-contract equivalence and fresh review passed before reset; delivery had been deferred by existing mixed working changes. Final integration/delivery must be recorded below. |
| Stable parameter/cache 036 | Upstream v0.35.0 records accepted source, hooks, review, architecture and real CPU PipelineController/ClearmlJob miss/routing-only hit/weight-decay miss, with active-task reads and downloaded GT/best-checkpoint hashes. Its workload ran locally under SDK simulated-remote settings; this proves server-backed lookup, not ClearML-agent scheduling. Separately, local checks, installed-package probes and CPU/Gloo recording-boundary tests passed; on 2026-10-20 real CPU/single-GPU publication/download/reload and diagnostic/plain controller miss-hit-miss repeats passed. One earlier local remote model-enrichment failure remains unexplained; neither upstream acceptance nor later local success establishes its cause, a source fix or a reliability guarantee. Final cleanup integration/delivery is recorded below. |
| Accurate startup/early publication 037 | Implemented, source-reviewed and delivered in v0.35.0. Persistent resumed CPU cache and paired pipelines verified active run/General/run_overrides, early GT/calibration/dashboards, aggregate timing, once-only uploads, exact downloads/checkpoints and readable reports. Actual scheduled execution remains not-run: T013 and the acceptance portion of T016 remain open, and its architecture acceptance fails only that native gate. Renewed explicit user authorization permitted Git-only delivery with the disclosed gap; delivery is not full acceptance. Physical multi-GPU, other native presets and real ONNX/TensorRT execution were not established by these scoped runs. |

Upstream early-publication 037's earlier direct single-GPU, CPU/Gloo DDP and queue snapshot/worker-loader
observations remain dated historical evidence; their earlier temporary raw archives were unavailable during
resumed release. Fresh persistent resumed evidence covers CPU controller lookup and paired pipelines. Actual
queue submission/loader testing did not establish scheduler admission; normal attempts stayed pending under
memory policy without bypass. Synthetic data does not establish model accuracy. Exact-tag wheel/source
installs reused prepared dependencies on Python 3.12.13 and do not prove fresh dependency resolution or
Python 3.13 execution. Corresponding portable guidance was delivered separately as v0.2.10 at
`351fde30139095668d40c7ee917b6276704bdc5e` in custom-opencode-skills; the former corp-skills alias
redirects, and that delivery did not replace installed skill copies.

The historical 029/031 waiver is an acceptance disposition, not a passing test or runtime relaxation. It
does not cover CUDA 11.8, future target certification or early-publication 037's pending scheduler gate.
Feature 036's live gate passed upstream and was independently checked locally on 2026-10-20. New 037's
successful source review and explicitly authorized delivery do not complete its missing native acceptance. A
future request to certify a waived target starts new scoped acceptance and review; no old external-input
request is silently reopened.

## Historical provenance

**Archival checkpoint H:**
[`d74945c83dc24094c599388bbcfd5e987daeb9bf`](https://github.com/BuckanovNikita/clearml-yolo/commit/d74945c83dc24094c599388bbcfd5e987daeb9bf).
All 548 retired files, including formerly uncommitted records, exist byte-for-byte in this ordinary reachable
commit. Their combined size is 3,563,396 bytes. The snapshot preserves documents and is distinct from commits
that originally implemented behavior. Its
[history map](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/037-cleanup-baseline/history-map.json)
inventories exact paths, SHA-256 values, sizes, destinations, topics and dispositions; the map excludes its
own recursive fingerprint. The map's SHA-256 is
`9568e0755bee0b056657e86f66bf1dee645aced6b86f7ada39c411a3add8b4d6`.
Coverage includes old feature directories, `.specify/bugs`, `.specify/assessments`, `docs/evidence` and the
three selected standalone dated reports. Existing commits, branches and tags were not rewritten or deleted.

Retrieve any original document with `git show H:path/to/document`, list it with `git ls-tree -r --name-only
H -- specs .specify/bugs .specify/assessments docs/evidence`, and inspect historical changes with `git log
--follow H -- path/to/document`. Here H means the full checkpoint SHA recorded above, not a branch name.
Original source commits below are immutable anchors, not blanket current acceptance.

| Content or decision | Original commit | Historical source at H |
| --- | --- | --- |
| Initial composed/native workflow | `93ef462faac0a5929e4b48d64730c3bf53d110be` | `specs/001-release-030/` |
| Native configuration groups | `23f864510abe0dc5a8d90546954f7e1dc670577d` | `specs/003-ultralytics-config-groups/` |
| CSV dataset/native model publication | `589dc4a563e8a767a3cf9b675df66820b0a3c83b` | `specs/008-dataset-clearml-tracking/` |
| Historical task recovery amendment | `db33015eb1b5d88050ce6e592002e3abc0b14bd7` | `specs/012-remove-legacy-compatibility/contracts/task-recovery.md` |
| Full evaluation evidence | `0946121fd91edecaf873df1a074f8146e46d0480` | `specs/014-evaluation-publication/` |
| Clean Python boundaries | `493f0399fc10c2f99ac072335115f754176baa14` | `specs/021-clean-architecture/` |
| Detector families and export | `43f9e7dc85672bbb25f29e6abcb27344201ac443` | `specs/025-multi-model-backends/verification.md` |
| Shared scientific/workbook extraction | `55dcabd87f002502f59fe55b8910f161be01da62` | `specs/028-shared-extraction/` |
| Direct execution/shared queue | `31a5bd5edc2fe122791005526ae747e7fe5b0401` | `specs/029-shared-cy-queue/` |
| Generation-fenced physical GPU freeing | `dcbbc4903cec07c67ce50cd9b116ea3f6dab8216` | `specs/031-test-quality-gpu-controls/gpu-control-simplification/` |
| Input correctness/document checks | `bdf21a63be95151759c58d2d701735b548c4baaa` | `docs/evidence/2026-10-15-correctness-cleanup/` |
| Explicit external acceptance waiver | `c168e62e71536246f2ad9a09af307850d8af3708` | `docs/evidence/2026-10-16-acceptance-closure/decision.md` |
| Readable shared queue/archive | `c3e3f15c7e907ab86d0bf8ccad703654828b0968` | `specs/034-readable-shared-queue/` |
| User config and NFS eligibility | `f64e973aaed25b2467615947387c5d115e39d585` | `specs/035-queue-user-config-nfs/` |
| Private refresh failure isolation | `ac65f80ec74926edca3a1409d3847dec9902124d` | `.specify/bugs/queue-view-refresh-isolation/` |
| Stable parameters/controller cache | `2e4b5f2fa3c3e9dc90920af75fe3edb8e346bcd0` | `specs/036-stable-clearml-cache/` |
| Accurate startup and early complete publication | `fd395d34bff7f3128047e5d0c302f2c3f0720b78` | `specs/037-early-accurate-publication/` |
| Integrated publication review/native evidence | `b4a8164feb486a3864af2e2cfec96501963c2df0` | `specs/037-early-accurate-publication/review.md` |
| Application v0.35.0 | `accdfb664b2c9f605b026b26d713cae4213e05e2` | `specs/037-early-accurate-publication/verification.md` |
| Sequential release verification and retained acceptance limit | `41a4036666b2225a4e3029e1695499cf914a5f59` | `specs/037-early-accurate-publication/verification.md` |

### Preserved executable fixtures

The scientific pre-extraction fixture moves from `specs/028-shared-extraction/baseline.json` to
`tests/fixtures/shared-extraction-baseline.json`, preserving SHA-256
`ba41b1cc32671847b29190457508fb696c3f1049460f945d81b1a30979b33117`. The module migration map moves from
`specs/021-clean-architecture/migration-map.json` to `tests/fixtures/legacy-module-map.json`, preserving
SHA-256 `7522e4bd8e521bfddfbedf48ec77faf03bed2b1cd3091c44c222523d6a81d715`. The original paths remain
recoverable at H. Tests consume the maintained copies; relocation never regenerates expectations or
reinterprets the baseline.

### Superseded designs

Historical GPU features 013/022/024 describe prior FIFO, waiting and four-control-mode designs; today's
direct/queue split and physical controls supersede them. Old project-local SDK redirection gives way to
normal SDK discovery and explicit retained project scratch. Current-only recovery restrictions were
deliberately amended by ordered historical threshold/checkpoint recovery. Old artifact copies, duplicate
summaries, per-class/per-normalization plot inventories and visible full-ID banners do not describe new
publication. Old submodule setup and published-package/assets delivery recipes are not current setup or
release authorization.

### Cutover acceptance

On 2026-10-20, ordinary merge `9fc0b50db12437ec669daa4ae543c3e7ca1c761f` reconciled the local cleanup
checkpoint and published v0.35.0 history. Its normal hooks passed Ruff, mypy, all 43 import contracts,
Vulture and the full pytest suite. A separate integrated architecture run passed 246 tests. Both final
wheel and sdist passed installed checks against all 184 package-file hashes, 12 console commands, nine
default/81 selected configurations, nine shipped callables, overwrite/mode checks and two queue snapshots.
Source-manifest SHA-256 is `b26afdab1d9620f627d583be6af7980ea3df9158f815689a919838da616d831f`.
These Python 3.12.13 checks reused dependencies; they add no Python 3.13 or hardware certification.
The [dated verification](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/037-cleanup-baseline/verification.md)
and [fresh independent review](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/037-cleanup-baseline/review.md)
retain initial, interrupted and successful outcomes separately. Final review returned ship after correcting
a duplicate-link replacement bug in the cutover helper.

The real dry-run and applied cutover both verified all 548 archived files before removal. Post-cutover
checks confirmed one file under `specs/`, both fixture hashes unchanged, all 52 snapshotted workflow-tool
paths unchanged, 20 historical commit/source references resolvable, and all 38 retained historical links
redirected to H. Source, tests, dependency configuration and executable contracts are unchanged since H.
The ignored active-feature pointer is absent. The installed creation script's read-only dry-run selected
`001-next-work` without creating a feature or pointer. All 34 retained Markdown files passed structure and local-link validation through the cutover
commit procedure; final Git delivery is recorded below.

The final documentation-only architecture record passed planning before removal and acceptance afterward:

```json
{
  "schema_version": 1,
  "task": "Verified history cutover to stage-zero baseline",
  "scope": [
    "specs",
    ".specify/bugs",
    ".specify/assessments",
    ".specify/feature.json",
    "docs",
    ".agents/skills/running-end-to-end-tests",
    "AGENTS.md",
    "README.md",
    "TECH_DETAILS.md",
    ".specify/memory/constitution.md"
  ],
  "impact": "none",
  "rationale": "After the separately verified source/fixture integration checkpoint, cutover removes only byte-preserved historical records, redirects documentation links, records the single baseline and clears the ignored active-feature pointer. Runtime modules, supported interfaces, dependencies, executable architecture checks and installed workflow tooling are unchanged. Both live test fixtures were already relocated and verified before this boundary; removing their unused historical copies adds no runtime or import effect."
}
```

The `cleanup-code` personal skill was released and installed from private `agent-skills` commit
`7f635ce123332d5444f294909c6a753dea7d268e`, annotated tag `v0.7.2`. All six installed files match the
released source; fresh independent review and 102 offline checks passed. Only this skill was installed;
shared agent links and unrelated lock metadata were preserved. Automatic host loading was not tested.
Actual native CPU/single-GPU/cache observations remain in the private
[dated evidence archive](https://github.com/BuckanovNikita/agent-skills/blob/1ab7da0b6448971a0abb44b5ec8380304714cfbc/skills/clearml-yolo-environment/references/cache-cleanup-2026-10-20/acceptance.md).
Neither this cutover nor successful repeats resolve the unexplained enrichment failure or complete the
inherited early-publication scheduler gate.

### Delivery record (2026-10-20)

The cutover is published on application `master` at
[`228be7f4e8184667f39cb1ad797c4b00e6958022`](https://github.com/BuckanovNikita/clearml-yolo/commit/228be7f4e8184667f39cb1ad797c4b00e6958022).
The remote branch was verified against that commit. The native release helper reported no unreleased
semantic changes; version v0.35.0 and its existing tag at
`accdfb664b2c9f605b026b26d713cae4213e05e2` remain unchanged. This dated evidence update follows the
cutover and does not change runtime behavior. The exact local dependency-source section was preserved,
excluded from commits and restored unstaged after every attempt.

Portable usage links were published in `custom-opencode-skills` v0.2.11 at
[`e0ff164696d86eaca42e218623f6c9f03798f0ad`](https://github.com/BuckanovNikita/custom-opencode-skills/commit/e0ff164696d86eaca42e218623f6c9f03798f0ad),
with remote branch and annotated-tag targets verified. Package validation, four explicit Markdown checks,
45-file Markdown lint, discovery of all four skills, architecture validation and fresh link review passed.
Only three contract links and release evidence changed; examples and installed usage copies were preserved.
The original checkout's concurrent unrelated edits were untouched. Personal `cleanup-code` v0.7.2 source,
annotated tag and six installed files were also independently reverified against Git objects.

Task-owned native runs and remote data were cleaned as recorded in their private evidence. Both disposable
package environments and all six generated probe workspaces were removed after acceptance; verification
manifests and logs remain available. The current work starts from this specification and feature `001`;
retired pending checkboxes remain historical records, and the explicit limitations above remain in force.
