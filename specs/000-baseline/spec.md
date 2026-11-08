# clearml-yolo: functionality

## Purpose

Train, evaluate and compare detector families through reproducible native workflows.
An experiment must retain its inputs, configuration, model identity and scientific
results, with truthful publication and safe process ownership. Optional visualization
must never decide whether computation succeeds. [Terms](../../GLOSSARY.md) distinguish
executable inputs, provenance and scientific results.

This specification owns functional outcomes and failure rules. Linked references supply
exact public schemas, model presets and configuration/API inventories. Internal module,
process and storage organization may change while public formats, numerical behavior,
permissions and ownership remain compatible.

## Commands and configuration

Users compose pipeline, train, predict, validate, metrics, report, comparison, export
and ground-truth operations with Hydra. Full and partial workflows share the same
input validation and output identity. Users can export editable self-contained configuration
for one selected command/model without running it. Missing inputs remain explicit;
force export replaces only selected regular files, never unrelated files or symlinks.
Output paths remain project-contained;
configuration inspection and previews do not resolve assets or execute models.

Configuration retains native model settings and explicit overrides. Canonical replay
stores original selectors, nulls and frozen augmentation content; resolved files,
URLs and hashes are separate provenance. An Agent restores one independent snapshot
before backend/input validation and joins the submitted task. Missing canonical data
permits complete explicit inputs; empty or malformed canonical data fails. Agent CUDA
visibility controls logical devices. Reproducibility never depends on parent memory.

A Git warning checks the original launch directory once, including help/config and
multiruns. Working trees, submodules and unborn repositories qualify; bare repositories
do not. Inspection is bounded to five seconds and ignores inherited Git selectors.
Failure is advisory on stderr, changes neither stdout nor exit semantics, and never
modifies Git state. Detailed rules: [configuration and workflow contracts](../../docs/project-contracts.md),
[runtime isolation](../../docs/runtime-isolation.md), [input provenance](../../docs/input-provenance.md).

Every effective MULTIRUN, including one-job sweeps, gets one fresh shared
`multirun-YYYYMMDD-HHMMSS-<six-word-phrase>` UTC tag. Explicit tags survive;
ordinary RUN adds none. Queue snapshots freeze this group and replay retains it.

## Data and scientific results

Ground truth accepts local CSV or a ClearML dataset selected by ID or project/name
with optional version; version cannot accompany ID. Materialize root dataset.csv,
resolve relative image paths against the source CSV, resolve once per pipeline, and reject malformed
selectors. Unversioned selection resolves afresh on each invocation.

Preserve literal text labels (including numeric-looking names and `NA`), row order,
empty images, original geometry and source identity. Training requires CSV ground truth,
nonempty train/val and at least one valid training box; report dropped invalid boxes and
use the cleaned truth in later stages. Source images remain immutable. Dataset preparation
supports YOLO NDJSON/flat and native-detector COCO without letting native data options
replace CSV-owned class/split mapping. Invalid or ambiguous input fails contextually.

Prediction output records whether image names are basenames, stems or paths and binds
that mode to prediction bytes. Scoring requires canonical basenames and known membership;
ambiguous legacy predictions cannot silently enter evaluation. Cache reuse binds CSV bytes,
resolved media references, format and preparation version. Changed image bytes at unchanged
paths require explicit idle invalidation; invalid/incomplete caches remain for inspection.

Calibrate confidence on val once, then freeze thresholds for requested train/test evaluation
and comparison. Default evaluation covers train/val/test; missing requested splits fail.
Compare candidate and baseline by current reinference over the same corpus, class mapping
and split (test by default). Historical metrics cannot substitute. The automatic baseline
is the latest completed prod-tagged task excluding the current task; absence records a skip
and preserves candidate results, while an invalid explicit reference fails.

Filter malformed prediction geometry only in the evaluation copy, with contextual counts;
raw exports retain original values. All-invalid predictions behave as empty predictions,
producing false negatives for unmatched truth. Schema/confidence errors remain fatal.
Support greedy, Hungarian and IoU-prior matching, interpolated/continuous AP, finite IoU
and false-discovery parameters in [0,1], and the defined precision/tie/empty-value semantics.
AP includes geometry-valid low-confidence/NMS-suppressed predictions; fixed-threshold
matching uses its prepared population. Do not derive metrics by rematching rendered reports.

Preserve each original object and prediction through filtering, exclusion, calibration,
matching and final result rows. Results distinguish TP/FP/FN, background, excluded,
filtered and not-evaluated states. Source identity, not box-coordinate coincidence, joins
results. Prediction-only rows cannot acquire invented evaluation; unselected images cannot
expand the scoring population. Threshold equality is retained.

Reports show each model's available metrics even for one-sided classes; absent operands
are NA, never invented zeros. Per-model aggregates use that model's eligible population;
paired differences/statistics use the shared eligible population and defined multiple-test
correction. Unknown training counts remain unavailable and visible as report issues;
evaluation counts cannot replace them. Empty shared populations retain available metrics
with unavailable comparisons. Workbooks preserve original numeric values, literal class
names, layout and readable model/source identity. Tampered decorated workbooks fail ingestion;
undecorated historical workbooks remain readable.

Publish current-model confusion counts and percentage views from identical counts, and
one test precision-recall view from the authoritative AP population. Zero denominators and
missing ground truth remain truthful. Readable names distinguish model/split/role while
machine provenance preserves exact identities. Visualization cannot alter scientific values.

Historical comparison recovers one coherent checkpoint/threshold identity. Explicit
threshold maps win; otherwise use the documented ordered artifact sources and fail on a
present invalid source rather than silently choosing another. Select a unique marked best
Output Model, then a unique best-named model, otherwise the last registered model with a
warning. Existing model selection failure cannot fall back to arbitrary artifacts. Without
Output Models, use the documented artifact order. Recover original bytes and source lineage
without modifying source tasks or promising that an obsolete architecture will load.

[Experiment records](../../docs/experiment-records.md) supplies result/artifact schemas,
threshold-source ordering, workbook details and native settings;
[shared evaluation/reporting](../../docs/shared-evaluation-reporting.md) supplies the
numerical protocol. [Technical reference](../../TECH_DETAILS.md) supplies cache and routing
fields. These references refine the behaviors above rather than requiring knowledge of an
old execution to decide a new outcome.

## Models, augmentation and training capacity

Support Ultralytics YOLO, DEIMv2, RF-DETR, Faster R-CNN and FCOS with their native
checkpoint, class, preprocessing and training semantics. User overrides are validated;
unknown, inactive-family or unsupported controls fail instead of being silently ignored.
A trained checkpoint owns pipeline inference; a conflicting explicit model fails. Native
normalization is recorded separately from requested configuration. Single/distributed
training preserves global microbatch meaning and supervised group cleanup.

Faster R-CNN deployment supports ONNX export, TensorRT engine construction and fixed-corpus
verification. Bind checkpoint, class mapping, preprocessing, output interpretation and
artifact hashes; reject incompatible shapes/precisions/runtime capabilities. Export and
verification remain distinct outcomes, with original artifacts and diagnostic evidence.
The [backend contract](../../docs/multi-model-backends.md) and
[deployment contract](../../docs/tensorrt-deployment.md) supply exact presets, controls and
representations; unsupported combinations fail explicitly.
Default augmentation remains native. Custom Albumentations JSON disables conflicting
optional native transforms visibly, validates names/targets and freezes content/hash.
Normalize, tensor conversion and arbitrary executable transforms are rejected.
One first top-level Mosaic uses raw training donors, distinct when possible, with
replacement only when necessary; only a one-image dataset reuses its primary image.
Boxes/classes/crowd/instance identity remain aligned; final normalization happens once.
See [augmentation](../../docs/augmentation.md) for geometry, reproducibility and dataset rules.

Capacity estimation measures once per model/resolution/profile and distinct GPU
name/capacity, with isolated GPU ownership and nonoverlapping trials on each assigned device.
The aligned search uses an eight-image grid, rounds ceilings down, requires capacity
at eight and independently confirms its winner. Cache hits need no idle GPU. Failure
of one case does not kill peers; supervision failure does. Only the invocation owner
promotes matching results after successful exit and verified cleanup. Forced results
remain explicitly background-sensitive. Coverage listing is offline and never promises
compatibility with a future allocation.

Null training batch requests strict local lookup: prefer exact allocation evidence,
otherwise use N times the minimum compatible single-GPU capacity across target hardware.
Unsupported profiles require explicit batch; unaligned old values cannot supply automatic
lookup. Training OOM fails without hidden retry/reduction. Rank failure terminates its
owned cooperating group before another trial or allocation contraction. Discovery-time nonfinite computation may
repeat once from fresh state; repeated numerical failure is not an OOM capacity result.
Force permits background utilization but never foreign compute ownership or unknown
telemetry. Exact settings,
strategies and serialized compatibility: [batch estimation](../../docs/batch-estimation.md)
and [batch interfaces](../006-batch-training/contracts/interfaces.md).

## Weights and offline operation

Explicit local assets are authoritative and missing files fail. Standalone selected-model
execution may use validated caches, configured proxies and original upstream sources;
bulk preparation uses pinned project archives and fails for uncovered/unavailable assets.
Manual offline placement requires no online receipt. Downloads use bounded retries,
per-asset locks, temporary files, atomic publication and identity/content checks.
Reject traversal, links, special files, duplicate members and forged Hub identity.
Hub weights/config must share the real snapshot commit; conversion provenance and
asset-specific licences survive redistribution, including DINOv3 notices.

Explicit preparation retries unresolved assets; automatic execution suppresses repeated
completed catalogue/location fingerprints, including partial failures, but not interrupted
attempts. Changed identities/destinations trigger another attempt. Native cache discovery
preserves model selectors. Native weight-cache selection is absolute and verified under concurrent access;
unrelated SDK settings stay intact. Imports/help remain inert. Missing-asset
errors identify original URL, exact destination, override and access requirement without
credentials. [Model assets](../../docs/model-assets.md) owns catalogue, proxy and cache rules;
[manifest format](../009-release-weights/contracts/manifest.md) owns archive metadata.

## Publication and process ownership

Experiment commands require ClearML and one invocation owner. Configuration export,
cache maintenance and inspection create no experiment task. Record executable inputs,
consumed dataset/report configuration, sanitized scientific parameters and source code
identity before work. Missing source Git identity warns without claiming that uncommitted
changes are captured. Agent execution preserves its submitted task identity.

Publish effective ground truth once, one complete combined result table after all enabled
contributors finish, full-precision validation thresholds, split dashboards, paired reports,
stage outcomes and operation-produced deployment artifacts. Training publishes one verified
best Output Model and owner telemetry. Verify model association, downloaded bytes/hash and
metadata readback; flush alone is insufficient. Only the owned verified model receives its
matching calibration thresholds; standalone metrics never creates or mutates models.

Preserve local outputs on publication failure. Never publish an incomplete aggregate or
silently retry uncertain scientific delivery. Standalone commands and skip-training
pipelines fail on required computation/publication failure. A pipeline with verified
successful training preserves that outcome when a downstream stage fails, recording explicit
warning completion and failed/skipped stages; fatal interruption still fails. Finalization
is bounded and cannot replace the original computation exception. Optional visualization
failure cannot rewrite scientific outcomes. Exact required inventory and result formats
are in [experiment records](../../docs/experiment-records.md).

Direct execution owns its process tree and protects unrelated/reused PIDs. Direct execution requires no queue admission or reservation. The separate cy-queue
depends on CY, never the reverse.
Queue workers execute only their owner's jobs, preserve snapshots and reservations,
and hand off extra GPUs only after durable contraction and acknowledgement. Missing
notification retains all devices; lost acknowledgement stops inference without restoring
extras. Worker death does not free live allocations; uncertain cleanup requires recovery.
[Queue lifecycle](../../docs/queue.md) and [diagnostics](../../docs/diagnostics.md) define
storage eligibility, cancellation, generation fencing, redaction and output capture.

## Local cache maintenance

`cy-dedup` explicitly deduplicates an idle image cache by exact case-sensitive filename
and identical bytes. Linux reflinks share blocks while keeping independent subsequent
writes. Preserve paths, content and file metadata; skip symlinks, hardlinks, cross-device
files and unsupported platforms without hardlink/copy fallback. Changed files cannot be
replaced. Failure reports prior successful replacements and cleans owned temporary files.
Dry-run mutates nothing and does not probe reflink support. Writable selections stay inside
CY_HOME; external selections are dry-run only. Counts describe files, not measured saved
bytes. See [selection and exit formats](../../docs/experiment-records.md#explicit-cache-deduplication).

## Compatibility

Public CLI/API, serialized formats and scientific values are compatibility boundaries.
Supported interpreter and dependency requirements are defined by [development](../../docs/development.md) and package metadata.
Default installation includes runtime capabilities; system drivers and approved external
source dependencies remain explicit prerequisites. Dependency installation is never an
implicit side effect of model execution. [Import boundaries](../../docs/import-boundaries.md)
describe internal implementation ownership, not additional product behavior.
