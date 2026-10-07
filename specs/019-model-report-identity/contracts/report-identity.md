# Report identity contract

New evaluation dashboards, plots, and every sheet of evaluation, statistical,
developer, and business workbooks show the model name and full source training task
ID. Printed worksheets repeat that identification on every page. Paired reports
identify baseline and candidate separately. Unknown training provenance is displayed
as `Training task: unavailable`.

`model_label` identifies unknown standalone prediction, validation, metrics, and
skip-training pipeline inputs. Comparison model references each accept `label`.
Standalone reporting accepts `baseline_label` and `candidate_label` for historical
inputs without stored identities. A custom label is not a uniqueness guarantee.
Stored source identity wins over fallback labels.

Finalized training identity is stored with checkpoint association in model metadata,
local checkpoint sidecars, prediction provenance, evaluation contexts, and comparison
manifests. Readers validate present provenance; malformed or stale data fails clearly.
Report-producing task IDs must never replace source training task IDs.

Artifact names and output paths remain stable. Repository adapters recognize annotated
and unannotated dashboards for report generation and threshold recovery. The pinned
dependencies and historical ClearML artifacts remain untouched. Metric values,
formulas, headings, styles, and model-specific class populations remain intact.
