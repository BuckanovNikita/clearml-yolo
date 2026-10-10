# Report identity contract

New evaluation dashboards, local raster plots, and every sheet of evaluation, statistical,
developer, and business workbooks show the model name and full source training task
ID. Printed worksheets repeat that identification on every page. Paired reports
identify baseline and candidate separately. Unknown training provenance is displayed
as `Training task: unavailable`.

The [readable evaluation plot amendment](../../020-readable-evaluation-plots/contracts/plots.md)
supersedes this contract's original full-ID requirement for ClearML chart captions.
Current-model confusion charts use model name/split labels with selectable normalization;
PR combines class traces on test only. Internal identifiers remain in provenance and
workbook banners. Baseline charts and comparison tables are excluded from Plots while
downloadable reports and comparison headline single values remain available. Repeated
checkpoint/split publication reuses a display slot; unrelated collisions use readable
stage/ordinal suffixes.

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

The [current report layout](../../001-release-030/contracts/cli.md) moves aggregate
availability out of developer/business metric columns into compact
`<metric>-valid-class-count` summaries. Apply this layout before identity annotation;
the annotated and embedded original workbooks both retain those summaries.
