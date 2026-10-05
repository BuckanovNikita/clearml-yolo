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
| run, consumed dataset, explicit report configuration | Canonical Configuration Objects; native General owns training arguments |
| Source links and meaningful requested/effective differences | Canonical run configuration, including missing automatic-baseline reason |
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
Configuration Object. Config-init creates no task/publications.

Result-only sections such as `evaluation_result` and `fiftyone_result` stay separate from
executable `evaluation` and `fiftyone` inputs. Remote clones ignore result-only roots and
reconstruct typed command inputs from canonical run settings plus native General.
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
