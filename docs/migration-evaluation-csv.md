# Evaluation table export migration

Evaluation and comparison exports now reserve XLSX for dashboards and metric tables. Other
tabular data is written as CSV so row-level evidence and metadata do not depend on Excel cell
conversion and size limits.

For each evaluated split, `metrics_evaluation_<split>.xlsx` contains only these sheets:

- `summary`
- `per_class`
- `confusion_matrix`

The removed sheets are available beside the workbook:

| Previous workbook content | Current CSV |
|---|---|
| ground-truth matches | `metrics_evaluation_<split>_ground_truth_matches.csv` |
| prediction matches | `metrics_evaluation_<split>_prediction_matches.csv` |
| thresholds used for the split | `metrics_evaluation_<split>_thresholds.csv` |
| evaluation methodology | `metrics_evaluation_<split>_methodology.csv` |

`metrics_best_confidences_val.csv` remains the canonical full-precision validation-threshold
artifact. ClearML table publication deduplicates by content, so an identical sidecar may be
represented by an alias to an already uploaded table.

For completed comparisons, `compare_workbook_<split>.xlsx` contains only the `Сравнение`
sheet. The excluded-class and methodology tables move to
`compare_workbook_<split>_excluded.csv` and `compare_workbook_<split>_methodology.csv`.

When automatic baseline lookup finds no baseline, `compare_evaluation_candidate_<split>.xlsx`
contains only `Classes` and `Summary`. Candidate thresholds and skip methodology move to
`compare_evaluation_candidate_<split>_thresholds.csv` and
`compare_evaluation_candidate_<split>_methodology.csv`.

Consumers that previously selected these tables by Excel sheet name must read the named CSV
sidecars instead. CSV columns preserve the corresponding table schema, and numeric exports use
full precision where the producing command previously required it. JSON manifests, evaluation
payloads and configuration data keep their JSON representation; PNG diagnostics keep PNG; final
technical and business reports remain XLSX.
