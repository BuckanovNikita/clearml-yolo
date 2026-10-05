# Publication inventory and adapters

| Current publication | Destination and contents |
|---|---|
| Native best checkpoint | One role-marked best Output Model |
| Native training/validation telemetry | Scalars, Plots and owner-only Debug Samples |
| ground_truth | One CSV artifact per distinct content |
| predictions | One canonical CSV artifact per distinct content/result |
| metrics_best_confidences_val | Full-precision CSV artifact, once per calibrated model |
| metrics_evaluation_SPLIT | XLSX artifact containing only summary, per_class and confusion_matrix |
| Evaluation row-level evidence | ground_truth_matches, prediction_matches, thresholds and methodology CSV sidecars |
| compare_workbook_SPLIT | XLSX artifact containing only Сравнение; excluded and methodology CSV sidecars |
| compare_evaluation_candidate_SPLIT | Skipped-baseline XLSX artifact containing Classes and Summary; thresholds and methodology CSV sidecars |
| report_dev_SPLIT, report_business_SPLIT | Final XLSX artifacts |
| run, consumed dataset, explicit report configuration | Canonical Configuration Objects; native General owns training arguments |
| Source links and meaningful requested/effective differences | Canonical run configuration |
| Preparation records, NDJSON, label archives, native YAML, raw metrics, dashboards, JSON/PNG diagnostics, comparison manifests, report inputs and publication receipts | Local files only; meaningful result links recorded in run configuration |

`expect_artifacts(task, names)` and `upload_artifact(task, name, path)` remain strict.
`publish_table(task, name, path)` performs table content deduplication and internally satisfies
aliases. No artifacts are silently skipped after expectation registration. Empty prediction
CSVs are valid. All required files must exist; model and artifact barriers precede completion.
`record_run_configuration(task, values)` merges sanitized nonempty sections into canonical run.
Adapter tests must assert exact inventories, including pipeline alias reuse and skipped stages.

Tabular publication uses XLSX only for dashboards and metric tables. Each evaluation workbook
is accompanied by `metrics_evaluation_SPLIT_ground_truth_matches.csv`,
`metrics_evaluation_SPLIT_prediction_matches.csv`, `metrics_evaluation_SPLIT_thresholds.csv`
and `metrics_evaluation_SPLIT_methodology.csv`. The canonical calibrated threshold artifact
remains `metrics_best_confidences_val.csv`; content deduplication may satisfy another table
name as an alias instead of uploading identical bytes twice. A completed comparison publishes
`compare_workbook_SPLIT_excluded.csv` and `compare_workbook_SPLIT_methodology.csv`. If automatic
baseline discovery skips comparison, `compare_evaluation_candidate_SPLIT.xlsx` contains only
Classes and Summary, with `_thresholds.csv` and `_methodology.csv` sidecars. JSON manifests,
payloads and configurations, PNG diagnostics and final report workbooks retain their formats.

Command inventory is the union of enabled owned stages: CSV train = truth + native model;
predict = truth + prediction; metrics = truth + prediction + validation thresholds + evaluation
workbooks and CSV sidecars; val = predict + metrics union; compare = truth + paired predictions +
comparison workbook and CSV sidecars (candidate evaluation workbook and its sidecars if automatic
baseline is absent); report = final reports;
ground-truth = truth; pipeline = deduplicated union. Every training inventory starts from CSV
truth and its consumed prepared-dataset Configuration Object. Config-init creates no task/publications.

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
