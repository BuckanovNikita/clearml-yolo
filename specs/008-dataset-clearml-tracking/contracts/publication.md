# Publication inventory and adapters

The [evaluation publication amendment](../../014-evaluation-publication/contracts/publication.md)
governs new canonical CSVs, full/DTRK dashboards, interactive plots and display identities.
This is a required inventory, not a claim that a particular native run has been verified.
Historical tasks and dated evidence retain their original names and contents.

| Current publication | Destination and contents |
|---|---|
| Native best checkpoint | One role-marked best Output Model |
| Native training/validation telemetry | Scalars, Plots and owner-only Debug Samples |
| `gt_csv` | One effective ground-truth CSV per invocation, retaining source lineage |
| `predicts_csv` | One combined CSV of all prediction/evaluation contexts per invocation, with original rows, statuses, thresholds and JSON match relationships |
| `metrics_best_confidences_val` | Full-precision validation threshold CSV |
| `metrics_dashboard_full_SPLIT`, `metrics_dashboard_dtrk_SPLIT` | Original full/DTRK evaluation XLSX workbooks per evaluated split |
| `comparison_ROLE_dashboard_full_SPLIT`, `comparison_ROLE_dashboard_dtrk_SPLIT` | Original full/DTRK comparison reinference XLSX workbooks; ROLE is candidate or baseline |
| Interactive evaluation plots | Four post-threshold confusion views and per-class PR curves per model/split context |
| `compare_workbook_SPLIT` | Paired XLSX artifact containing `Сравнение`; excluded classes in `compare_workbook_SPLIT_excluded` CSV |
| `report_dev_SPLIT`, `report_business_SPLIT` | Final paired XLSX artifacts |
| run, consumed dataset, explicit report configuration | Canonical Configuration Objects retain full replay settings; native General contains scientific training arguments |
| Source links and meaningful requested/effective differences | Canonical run configuration, including missing automatic-baseline reason |
| `export_onnx`, `export_engine` | Produced deployment graph or serialized engine, according to the export operation |
| `export_metadata` | Checkpoint/graph/engine hashes, classes, preprocessing, inference policy, runtime/plugins and profiles |
| `export_verification`, `export_corpus` | Verification report and fixed labeled corpus manifest from `cy-export export.operation=verify` |
| Preparation records, NDJSON, label archives, native YAML, raw metrics/predictions, match/threshold/methodology tables, duplicate evaluation summaries, JSON/PNG diagnostics, comparison manifests, report inputs and publication receipts | Local files only; meaningful result links recorded in run configuration |

`expect_artifacts(task, names)` and `upload_artifact(task, name, path)` remain strict.
`publish_table(task, name, path)` retains content deduplication and satisfies aliases.
The invocation bundle registers/enriches durable local context shards and assembles
`gt_csv`/`predicts_csv` exactly once in owner-only pre-finalization callbacks. Empty
prediction CSVs are valid. Required files must exist; callbacks precede model/artifact
barriers and flush. Registered expectations cannot be silently skipped.
`record_run_configuration(task, values)` merges sanitized nonempty sections into canonical run.

New uploads do not include `metrics_evaluation_*` summary workbooks, separate match,
threshold or methodology sidecars, raw prediction artifacts or a skipped-baseline
candidate summary workbook. Local diagnostics and historical recovery remain available.
XLSX publication preserves original full/DTRK dashboards and paired comparison/report
workbooks; exclusions and exact validation thresholds remain CSV. Interactive plots use
the SDK, not additional artifact files.

Command inventory is the union of enabled owned stages: train = effective GT + native
model/telemetry; predict = GT + not-evaluated combined prediction context; metrics/val =
GT + combined evaluated contexts + validation thresholds when calibrated + full/DTRK
dashboards + interactive plots; compare = GT + reinference contexts + candidate/baseline
dashboards + interactive plots + paired comparison workbook/exclusions when a baseline
exists. Missing automatic baseline retains candidate dashboards/plots and records the
skip reason. Report publishes developer/business workbooks; ground-truth publishes GT;
pipeline assembles canonical CSVs once. Training also records its consumed prepared-dataset
Configuration Object. Export publishes its operation-specific bundle and source identity
without another trained Output Model. Detector COCO annotations and checkpoint descriptor
sidecars remain local; the portable descriptor is embedded in the published checkpoint.
Config-init creates no task/publications.

Result-only sections such as `evaluation_result`, `fiftyone_result` and `export_result`
stay separate from executable `evaluation`, `fiftyone` and `export` inputs. Remote clones ignore result-only roots and
reconstruct typed command inputs from canonical run settings plus scientific native General overrides.
Prior owner-derived General project/name/save_dir never determine the clone output route;
current explicit routing requests and the new invocation identity own those paths.
Current explicit save_dir remains visible to pipeline conflict validation; remote replay
must reject the same invalid current routes as local execution.
Redaction applies to stored copies only; executable local inputs and explicit remote
overrides retain their original values.

Local dataset/configuration files follow the maintained
[filesystem ownership contract](../../../docs/filesystem-policy.md). CSV preparation owns the
native data reference and preserves source images. Invocation-owned resolved execution copies use
workspace temporary storage and are not publication artifacts.

Confidence plots published for an evaluation must be freshly generated. Before generation,
the adapter clears only its known legacy unsuffixed and current-split confidence plot outputs;
other split outputs and unrelated files remain intact. Both producer naming conventions are
supported, and missing fresh required plots fail instead of reusing an older file.

## Recovery compatibility (2026-10-05)

The inventory above governs new publications. Reading existing task models follows
[task-backed recovery](../../012-remove-legacy-compatibility/contracts/task-recovery.md),
including ordered historical threshold/dashboard and checkpoint sources. These readers do
not add legacy artifact uploads or rewrite historical tasks. Artifact-backed provenance records
source task/artifact identity; it does not invent an Output Model link.

## Cross-contract integration

ClearML publications follow the current inventory, not old artifact counts. Native
YAML, NDJSON, archives, manifests and diagnostic/publication receipts remain local.
Consumed dataset and explicit report configurations are Configuration Objects. Canonical
`run` supports replay through an explicit canonical-object read and a detached, sanitized
snapshot write; inherited SDK connection flags and proxy containers do not control execution.
YOLO retains full `run.ultralytics` settings and scientific `General` replay overrides.
New detector families replay `run.model` and record sanitized scientific native arguments
in `General` as observed evidence, without applying remote overrides to that evidence.
The [stable parameter amendment](../../036-stable-clearml-cache/contracts/cache.md)
defines execution-only exclusions, full replay preservation and opt-in controller cache
normalization. Configuration copies are not artifacts.
Native owner callbacks may publish training/validation previews and non-PR plots; native
validation PR uploads are filtered with callback state restored on success/failure.
Native DDP descendants do not publish.
The native best checkpoint uses one Output Model, verified before completion.
