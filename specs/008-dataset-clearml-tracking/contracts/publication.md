# Publication inventory and adapters

| Before | After |
|---|---|
| artifact_manifest, resolved/effective configuration dumps, source_hydra copies | Internal verification; canonical run Configuration Object only |
| training_model_reference, train_effective_arguments/output_location, train_data_overrides | run meaningful differences; native General training arguments |
| train_weights_best.pt / last.pt and native output model | One native best.pt Output Model |
| train CSV/plot files, batch previews omitted | Native Scalars, Plots, Debug Samples |
| dataset_preparation, labels.zip, dataset_ndjson | Local only |
| dataset_ground_truth, ground_truth, metrics_ground_truth, compare_ground_truth | One ground_truth CSV per distinct content |
| predict_predictions, metrics_predictions, compare_predictions_ROLE_SPLIT | One canonical prediction CSV per distinct content/result |
| metrics_best_confidences_SPLIT dictionary | metrics_best_confidences_val full-precision CSV, once per calibrated model |
| full/dtrk dashboards, raw metrics, matches, summaries, confusion PNG, plot files, evaluation JSON | metrics_evaluation_SPLIT XLSX containing only summary, per_class and confusion_matrix; ground_truth_matches, prediction_matches, thresholds and methodology CSV sidecars; local diagnostics retained |
| compare per-role dashboards/raw metrics/metadata/native ZIP, counts/exclusions/methodology dumps | compare_workbook_SPLIT XLSX containing only Сравнение; excluded and methodology CSV sidecars; source links in run configuration |
| comparison_manifest/status/model-reference dumps | Local manifest and meaningful run configuration fields |
| report input dashboards/manifest | Local inputs only |
| report_dev_SPLIT, report_business_SPLIT | Final XLSX workbooks retained |
| fiftyone_publication diagnostic receipt | Local receipt; meaningful link in run configuration |
| dataset/native/report YAML object plus artifact | Consumed dataset and explicit report object only; local commented native YAML |

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
ground-truth = truth; pipeline = deduplicated union. Native-YAML-only training publishes its
consumed dataset Configuration Object and native model; it does not produce a truth CSV.
Config-init creates no task/publications.

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
[filesystem ownership contract](../../../docs/filesystem-policy.md). Native-YAML training stages
real image and label copies in its locked workspace cache before native repair or cache generation;
the original YAML, images and labels remain read-only inputs. Invocation-owned resolved execution
copies use workspace temporary storage and are not publication artifacts.
