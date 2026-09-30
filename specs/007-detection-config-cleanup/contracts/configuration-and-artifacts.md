# Configuration, routing and artifact contract

Prediction device defaults to [-1], independently of training device=null. Other shared
references remain visible. Examples group active detection keys first, then commented
cy-controlled keys, then commented inapplicable keys; preserve upstream relative ordering
and every upstream comment. task/mode/data/project/name are controlled in both examples;
prediction also controls source/model. Training model/classes/fraction stay editable.
These groups still compose complete configurations; supported CLI overrides remain valid.
Runtime YAML includes actual derived values, including project, name, source, model and data.

Implicit roots: runs/<encoded-project>/<encoded-task>-<encoded-task-id>/ using the active
ClearML task. Explicit run_dir wins; explicit run_id retains runs/<run_id>. Standalone
output_dir defaults to <root>/<command-config-name>; output defaults to <root>/<name>.csv.
Direct prediction retains predictions.csv; native training retains detect/<safe-task-name>.
Pipeline stages retain detect/train, native/predict, predictions.csv, metrics, comparison
and reports. Encoding preserves ASCII alphanumeric, hyphen and underscore; other bytes
use percent encoding. Windows device names and the reserved latest shortcut name are encoded too. Empty components fail. Explicit paths retain existing semantics.

Default splits for cy, cy-val, cy-metrics: train, val, test. Calibration uses val once.
Each evaluated split publishes one consolidated metrics_evaluation_<split> workbook.
Exact validation thresholds are published once as metrics_best_confidences_val CSV. Shared
truth/prediction tables are deduplicated; local raw metrics/matching JSON remain available.
This replaces the earlier thirteen-artifact split inventory under the
[008 publication contract](../../008-dataset-clearml-tracking/contracts/publication.md).

cy-val does not publish to FiftyOne. Pipeline nested prediction/metrics do not publish to
FiftyOne. Matching fidelity, GT identity, media resolution and task-ID namespaces remain.
Installed native ClearML callbacks are enabled for the invocation owner and disabled for
workers; owner-only training telemetry and the single native best Output Model are permitted.

Standalone comparison accepts a split override and defaults to test. Pipeline comparison is
fixed to test. Reports follow the split in `comparison_manifest.json`. Every compared model
uses exact supplied thresholds or tracked validation thresholds, with historical per-split
payloads supported only as a compatibility reader; no compared split is recalibrated.
