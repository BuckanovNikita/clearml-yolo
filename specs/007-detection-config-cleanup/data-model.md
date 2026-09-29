# Data model

Task identity is a plain immutable project-name/task-name/task-ID tuple returned by the
ClearML adapter. All components must be nonempty strings. The filesystem encoder produces
one portable path component per string; explicit output roots bypass implicit identity.

Per-split inventory maps 13 unique artifact prefixes to produced tables/maps/files. File
values must exist before publication; successful tracked completion requires every upload.
Splits have distinct names and file paths and share identical val-calibrated thresholds.

MetricsResult.evaluations remains a split-to-path mapping. Schema-version-1 evaluation JSON
retains matching indices, labels, status, confidence and IoU. PublicationReceipt remains
invocation-level and references durable payloads under resolved owner output routing.
