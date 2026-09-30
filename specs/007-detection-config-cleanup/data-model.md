# Data model

Task identity is a plain immutable project-name/task-name/task-ID tuple returned by the
ClearML adapter. All components must be nonempty strings. The filesystem encoder produces
one portable path component per string; explicit output roots bypass implicit identity.

Each evaluated split has one consolidated `metrics_evaluation_<split>.xlsx` performance
artifact. One full-precision `metrics_best_confidences_val.csv` artifact stores the frozen
validation thresholds shared by evaluated splits. Raw dashboards, metrics, matches, plots,
confusion images and evaluation JSON remain local diagnostics. Required published files must
exist before successful tracked completion.

MetricsResult.evaluations remains a split-to-path mapping. Schema-version-1 evaluation JSON
retains matching indices, labels, status, confidence and IoU. PublicationReceipt remains
invocation-level and local; its meaningful dataset/run identity is recorded in canonical run
configuration under resolved owner output routing.
