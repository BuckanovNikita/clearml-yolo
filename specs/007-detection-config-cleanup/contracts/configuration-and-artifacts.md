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
Each evaluated split has exactly these 13 artifact prefixes plus its split suffix:
metrics_dashboard_full, metrics_dashboard_dtrk, metrics_matches_gt, metrics_matches_preds,
metrics_confusion_matrix, metrics_summary, metrics_raw, metrics_best_confidences,
metrics_plot_recall, metrics_plot_precision, metrics_plot_perebrak, metrics_plot_nedobrak,
metrics_evaluation. Missing files or unsuccessful uploads fail the invocation.

Shared input/methodology artifacts and the one fiftyone_publication receipt are excluded.
cy-val never publishes. Pipeline nested prediction/metrics never publish. Schema/version,
matching fidelity, GT identity, media resolution and task-ID publication namespaces stay
unchanged. Comparison and developer/business reports remain test-only.
