# Reports

Reports present evaluation and comparison results to people without changing any
scientific value. `cy-report` reads a finished `cy-compare` directory and writes paired
developer and business Excel workbooks; the `cy` pipeline runs the same step after a
successful comparison. Every workbook produced by evaluation, comparison or reporting
carries a readable identity footer, keeps table headers in place, shows original
training counts with explicit warnings when they are unknown, and stays machine-readable
so later stages can recover the original metrics exactly. ClearML charts for the current
model are published alongside.

## Behavior

### Report workbooks

`cy-report` loads `comparison_manifest.json` from `comparison_dir`, takes the
candidate and baseline full dashboards and the split it names, and writes
`report_dev_<split>.xlsx` and `report_business_<split>.xlsx` in `output_dir`. A
standalone run publishes only these two final workbooks (as `report_dev_<split>` and
`report_business_<split>`) and, when given, the report configuration.
`report_config_path` selects a custom report-generator configuration; it is attached to
the task as the `report` configuration. Inputs must be
per-model dashboards (with `ap50` or `f1_score`); the statistical comparison workbook is
rejected. Deltas are `candidate - baseline`.

Classes that only one model has keep their measured values; absent operands and
comparisons show `NA`, never zero. Each model's averages and business inputs use its own
eligible classes; differences use the shared eligible classes. Exact text labels survive,
including `0001` and literal `NA`. A class is eligible when its training count reaches
the report-generator `min_train_count` (20 by default; a custom `report_config_path` can
change it). Classes below it leave the metric sheets and appear on the
`Удаленные классы` sheet. Numeric cells in the class column, such as threshold footer
values, are not classes. Below each metric table, aggregate availability is
shown as `<metric>-valid-class-count` rows (for example `AP50-valid-class-count`) with
`valid/eligible` fractions, including `0/N` and `0/0`.

### Other workbooks

Evaluation writes `full_dashboard_<split>.xlsx`, `метрики_дтрк_<split>.xlsx`,
`matrix_<split>.xlsx` and `metrics_evaluation_<split>.xlsx`; comparison writes
`compare_workbook_<split>.xlsx` or the candidate-only workbook. All of them follow the
identity, alias and count rules below. Original numeric values, formulas, styles, merged
ranges, filters, panes and print settings are preserved.

### Identity footer

Every sheet ends with an identity footer starting after one empty row below its last
cell, merged range or drawing. For each role (`model`, `baseline`, `candidate`) it shows
`<Role>: <model name>` and either `Training task: open in ClearML` or `Training source:
recorded` / `Training source: unavailable`, followed by the alias notice `Class labels
use readable aliases; original values are retained.` when any visible text in the
workbook was replaced by a readable alias. When the invocation's ClearML session knows
the web host, the role line links to the model page (when a model ID is recorded) and
the training-task line links to the source training task; otherwise the lines are plain
text and the report still succeeds. Links never target the task writing the report.
Every printed page carries a plain-text page footer `<Role>: <model name> · Training
source: recorded|unavailable` (at most 255 characters); no print-title rows are added
and printed width fits one page.

Visible cells, captions and footers show names and roles, never task IDs, model IDs or
checkpoint digests; an opaque identifier in a visible cell is shown as a readable
placeholder. Exact identities live in hidden workbook metadata. Formula-like names are
written as literal text.

### Machine readability

Hidden metadata stores each role's identity and a fingerprint; a second envelope keeps
the exact original workbook when class labels receive readable aliases (distinct opaque
labels get distinct aliases). Readers validate both and recover the original bytes
before reading metrics. An annotated workbook edited after annotation fails ingestion.
Workbooks without metadata remain readable; a reader that ignores the metadata sees the
footer as trailing rows. Re-annotating starts from the recovered
original and yields one footer.

### Training counts and warnings

Dashboards show the training count column `Количество примеров train` from the
evaluated checkpoint's own training population, never from the evaluation population.
Counts come from the current invocation's training or, for an existing model, from the
original training task's `gt_csv` after checkpoint ownership and SHA-256 are verified.
Unknown, malformed or unverifiable counts stay `NA`; a valid zero stays zero; a class
absent from a verified split counts as zero. Every split uses the model's `train`
counts for eligibility. Report input dashboards that already carry valid counts are used
as declared.

When a class has no valid count, evaluation dashboards and reports keep its metrics in an
`Unknown training count` sheet, exclude it from count-dependent aggregates and deltas,
list it in a `Report issues` sheet (model, class, field, reason, impact) and open on
that sheet; other sheets get a warning comment on their first cell. An entirely unknown
population produces unavailable summaries. The `report` stage of a pipeline then ends
with a warning outcome.

A `Dataset counts` sheet in evaluation and comparison workbooks lists, per role, the
original annotation count of every class in every prepared split (background rows
excluded), separate from current evaluation counts. Missing evidence shows `NA`.

### Readable plots and charts

Confidence-interval plots carry a caption with the model name and training-source
status. In ClearML, each current-model split gets one `Confusion matrix` chart that
opens on `Counts` and switches to exactly one of `Counts`, `Row %`, `Column %` and
`Overall %` of the same post-threshold counts (true rows, predicted columns, class order
and background kept; percentage views share a 0–100 scale, hover keeps the integer count
and its denominator, and zero
denominators show zero and `no observations`). The `test` split also gets one
`Precision-recall` chart at IoU 0.50 with every class, its AP50 and AP method in the
legend and confidence and cumulative TP/FP on hover; classes without ground truth or
predictions keep a legend entry without points. Series are named
`<model name> · <split>`; repeated publications reuse their slot and collisions get
readable stage or ordinal suffixes. Opaque class labels receive the same distinct
readable aliases in plots and charts as in workbooks. Baseline charts never appear in
Plots.

### Labels for unknown sources

A model without recorded provenance needs a name: `model_label`, a model reference
`label`, or `baseline_label` / `candidate_label` for report inputs whose dashboards
carry no identity. A recorded identity always wins over a supplied label, and a label never
invents a training task (`Training source: unavailable`). Quote Unicode labels inside the
override, for example `'model_label="experiment-Ω"'`. A stored identity that disagrees
with the comparison manifest fails.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `comparison_dir` | required | `cy-compare` output with `comparison_manifest.json` |
| `output_dir` | task-owned route | Destination |
| `report_config_path` | `null` | Custom report-generator configuration |
| `baseline_label`, `candidate_label` | `null` | Names for inputs without identity |

The pipeline exposes `report.report_config_path` and `skip_report`.

## Failure behavior

- A missing manifest fails with `run cy-compare first`; a missing dashboard fails with
  `Comparison candidate dashboard does not exist` (or baseline).
- An edited annotated workbook, invalid identity metadata or an identity that
  contradicts the manifest fails before metrics are read.
- Unknown training counts never fail a report; they produce the issue sheets.
- Missing ClearML links never fail a report.
- Upload failures fail standalone `cy-report` and keep the local workbooks.

## Limits

- Historical workbooks are read, never rewritten.
- Count recovery for an existing model needs its original training task's `gt_csv` and
  verifiable checkpoint ownership; otherwise counts stay unknown.
- Readable rendering never changes metric values, source rows or thresholds.

## Code and tests

- [`application/use_cases/report.py`](../../src/clearml_yolo/application/use_cases/report.py):
  workflow and identities.
- [`adapters/reporting/`](../../src/clearml_yolo/adapters/reporting/): report builders,
  identity footer, count issues, `Dataset counts`.
- [`adapters/clearml/report.py`](../../src/clearml_yolo/adapters/clearml/report.py),
  [`links.py`](../../src/clearml_yolo/adapters/clearml/links.py),
  [`population.py`](../../src/clearml_yolo/adapters/clearml/population.py): charts,
  links, count recovery; [`core/presentation.py`](../../src/clearml_yolo/core/presentation.py):
  readable text.
- Tests: [`test_report.py`](../../tests/test_report.py),
  [`test_report_class_availability.py`](../../tests/test_report_class_availability.py),
  [`test_report_count_issues.py`](../../tests/test_report_count_issues.py),
  [`test_workbook_identity.py`](../../tests/test_workbook_identity.py),
  [`test_identity_flows.py`](../../tests/test_identity_flows.py),
  [`test_identity_links.py`](../../tests/test_identity_links.py),
  [`test_population_recovery.py`](../../tests/test_population_recovery.py),
  [`test_population_count_workbooks.py`](../../tests/test_population_count_workbooks.py),
  [`test_training_count_provenance.py`](../../tests/test_training_count_provenance.py),
  [`test_evaluation_identity.py`](../../tests/test_evaluation_identity.py).
- Real links to a ClearML web host are established only by the live suite.
