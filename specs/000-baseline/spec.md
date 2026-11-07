# clearml-yolo: functionality

## Purpose

Train, evaluate and compare detector families through reproducible native workflows.
An experiment must retain its inputs, configuration, model identity and scientific
results, with truthful publication and safe process ownership. Optional visualization
must never decide whether computation succeeds.

## Commands and configuration

Users compose pipeline, train, predict, validate, metrics, report, comparison, export
and ground-truth operations with Hydra. Full and partial workflows share the same
input validation and output identity. Output paths remain project-contained;
configuration inspection and previews do not resolve assets or execute models.

Configuration retains native model settings and explicit overrides. Canonical replay
stores original selectors, nulls and frozen augmentation content; resolved files,
URLs and hashes are separate provenance. An Agent restores one detached snapshot
before backend/input validation and joins the existing task. Missing canonical data
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
preserve existing image-path semantics, resolve once per pipeline, and reject malformed
selectors. Unversioned selection resolves afresh on each invocation.

Preserve literal labels, image/content identity, split exclusions, geometry conventions,
empty images and exact numerical policies. Predictions bind naming mode to bytes;
ambiguous legacy identities cannot silently enter scoring. Comparison uses the same
resolved corpus and class mapping; automatic baseline selects the latest completed
prod-tagged task excluding the current task. Required original content is recoverable
byte-for-byte, including remote model/configuration artifacts.

[Experiment records](../../docs/experiment-records.md), [shared evaluation/reporting](../../docs/shared-evaluation-reporting.md)
and [technical reference](../../TECH_DETAILS.md) own exact metrics, result schemas,
workbook semantics, dataset cache rules, output routing and historical model recovery.

## Models, augmentation and training capacity

Native backends retain their checkpoint, class, preprocessing and export semantics.
The [backend contract](../../docs/multi-model-backends.md) defines supported presets,
training modes and deployment representations; unsupported combinations fail explicitly.
Default augmentation remains native. Custom Albumentations JSON disables conflicting
optional native transforms visibly, validates names/targets and freezes content/hash.
Normalize, tensor conversion and arbitrary executable transforms are rejected.
One first top-level Mosaic uses raw training donors, distinct when possible, with
replacement only when necessary; only a one-image dataset reuses its primary image.
Boxes/classes/crowd/instance identity remain aligned; final normalization happens once.
See [augmentation](../../docs/augmentation.md) for geometry, reproducibility and dataset rules.

Capacity estimation measures once per model/resolution/profile and distinct GPU
name/capacity, with independent GPU-pinned processes and sequential trials per case.
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
owned cooperating group before another trial or allocation contraction. Exact settings,
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
preserves model selectors. Ultralytics weights_dir becomes absolute under a lock with
readback; unrelated SDK settings stay intact. Imports/help remain inert. Missing-asset
errors identify original URL, exact destination, override and access requirement without
credentials. [Model assets](../../docs/model-assets.md) owns catalogue, proxy and cache rules;
[manifest format](../009-release-weights/contracts/manifest.md) owns archive metadata.

## Publication and process ownership

Required ClearML data, configuration, model, console/scalar and report publications
follow [experiment records](../../docs/experiment-records.md). Original selectors and
source identities stay distinguishable from effective runtime inputs. Completion follows
required publication and cleanup; uncertain delivery is not replayed automatically.
Optional FiftyOne/visualization failures do not rewrite scientific outcomes.

Direct execution owns its process tree and protects unrelated/reused PIDs. Shared
supervision stays in CY; the separate cy-queue depends on CY, never the reverse.
Queue workers execute only their owner's jobs, preserve snapshots and reservations,
and hand off extra GPUs only after durable contraction and acknowledgement. Missing
notification retains all devices; lost acknowledgement stops inference without restoring
extras. Worker death does not free live allocations; uncertain cleanup requires recovery.
[Queue lifecycle](../../docs/queue.md) and [diagnostics](../../docs/diagnostics.md) define
storage eligibility, cancellation, generation fencing, redaction and output capture.

## Local documentation and compatibility

cy-docs serves an offline Russian reference with searchable stable field links,
effective defaults and authored tutorials. Users edit YAML/overrides, inspect differences
and download configurations. Previews are isolated, bounded to 100 jobs and 15 seconds,
reject external search paths/plugins, retain unresolved expressions and cannot train,
load datasets or instantiate targets. Shutdown reaps owned workers. Assets ship without
requiring Node. [Local documentation](../../docs/local-documentation.md) owns the UI contract.

Public CLI/API, serialized formats, scientific values and supported interpreter range
remain consistent with [development](../../docs/development.md) and package metadata.
Default installation includes runtime capabilities; system drivers and approved external
source dependencies remain explicit prerequisites. Dependency installation is never an
implicit side effect of model execution. [Import boundaries](../../docs/import-boundaries.md)
assign effects and shared interfaces; maintenance/release procedures belong outside this
product description.
