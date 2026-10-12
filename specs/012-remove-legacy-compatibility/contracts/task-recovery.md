# Task-backed model recovery

**Amendment approved**: 2026-10-05. This contract supersedes only the recovery restrictions
in [current-only.md](current-only.md); current publication remains unchanged. The approved
user plan overrides the historical constitution recovery prohibition without modifying
protected `.specify/` files. Other current-only application/configuration rules still apply.

## Threshold selection

An explicit threshold map on either model reference is authoritative. Otherwise inspect
source-task artifacts in this fixed order, independent of the comparison split:

1. `metrics_best_confidences_val`
2. `best_confidences_val`
3. `metrics_best_confidences_test`
4. `best_confidences_test`
5. `metrics_dashboard_full_val`
6. `dashboard_full_val`
7. `metrics_dashboard_full_test`
8. `dashboard_full_test`

Named threshold artifacts accept JSON mappings as objects or strings, pandas Series,
DataFrames, and downloaded CSV tables, including ClearML-uploaded DataFrame `.csv.gz`
files. Dashboard artifacts accept DataFrames and downloaded CSV/CSV.GZ/XLSX tables with a
`confidence` column. Threshold tables use class names as their index or a `class_name`
column, with `confidence` or a single remaining value column; dashboards require `confidence`. Preserve class names as strings, including numeric-looking names,
and retain available numeric precision. Reject empty tables/maps, duplicate or empty class
names, missing confidence values, unsupported shapes, nonfinite values and values outside
[0, 1]. A present higher-priority source that is malformed or cannot be downloaded fails
with task/artifact context; it never permits fallback to a later artifact. Fallback applies
only when a source is absent. Missing all supported sources is an actionable error.

Historical dashboards supply only stored thresholds, never historical predictions or
comparison metrics. Dashboard recovery warns that the stored confidence may be rounded
and calibration provenance is unavailable; it does not claim full original precision or
validation-only calibration. Thresholds remain frozen; comparison never recalibrates them.

## Checkpoint selection

When output models are registered, choose a unique model whose metadata marks `best`.
Multiple marked best models are ambiguous and fail. With no metadata-marked best, choose
a unique output model whose URL-decoded URL basename is `best.pt`, `best.pth` or `best.ckpt`; multiple such models
are ambiguous and fail. With neither marker, choose the last registered output model
and log that fallback. Never choose checkpoint artifacts while any output model exists,
and never download unselected output models.

Only when no output models are registered, inspect task checkpoint artifacts in order:
`train_weights_best.pt`, `train_weights_best.pth`, `train_weights_best.ckpt`,
`train_weights_best`, `best.pt`, `best.pth`, `best.ckpt`, `best`, `model`, `checkpoint`,
then other artifact names ending in `.pt`, `.pth` or `.ckpt`, sorted lexicographically. Select the first
present candidate, download only it, and require an existing local checkpoint. A selected
source download or validation failure is actionable and does not try later candidates.
Output-model downloads, including `clearml://` references, use the same validation.
Legacy `.pt` files remain supported. Ordinary task recovery and direct model-URI downloads
require embedded detector metadata for `.pth` and `.ckpt`; available descriptor sidecars
and remote hashes must match the downloaded bytes.

A native `ModelRef` may instead supply complete typed `backend`, `preset`, `class_names`
and `preprocessing` assertions. This supports raw checkpoints both locally and through
task-backed references: the assertions accompany recovery of the selected Output Model
or task artifact. The backend must select a native detector family, not `ultralytics`.
Partial assertions do not relax checkpoint validation. Existing embedded metadata must
agree with all four asserted fields, and sidecar/hash checks remain mandatory when
available. Recovery preserves the downloaded bytes; it does not embed the assertions in
the raw checkpoint. Later references to those bytes still need the complete assertions.
Unasserted automatic task lookup and direct `clearml://` downloads retain the embedded
metadata requirement. The
[multi-model amendment](../../025-multi-model-backends/contracts/backend.md) extends these
suffixes and best filenames without changing existing YOLO priority or threshold recovery.

## Provenance and comparison

One selection result supplies both the downloaded weights and source provenance. An
output-model result records the source task/model identity and links; an artifact result
records the source task/artifact identity and has no fabricated model ID or model link.
Checkpoint contents, their validated descriptor or complete native assertions supply
labels and architecture. Recovery does not guarantee that an old checkpoint architecture
can load with the installed backend version, including Ultralytics for legacy YOLO;
load errors remain actionable rather than being hidden by choosing another checkpoint.

Baseline and candidate both use the same current ground-truth split images and current
inference/evaluation settings, including when either or both positions are historical
task references. Pipeline uses `test`; standalone comparison defaults to `test` and accepts
another current split. Reports consume the new paired results and manifest split. Recovery
does not fetch historical predictions or import source General/Configuration Objects over
current comparison settings. Current runs still publish one native best Output Model and
one full-precision validation threshold CSV; recovery does not rewrite source tasks.

## Identity retained by new results

New evaluations carry the selected source's finalized model name, full original
training task ID, checkpoint SHA-256 and registered model ID when available.
Output-model recovery reads stored identity metadata and checks its original-task
association; available checkpoint hash metadata must match downloaded bytes. For
historical records without identity metadata, use the selected source model/task's
display name and known original training association. Artifact-only recovery records
its source task identity without fabricating a registered model ID. Never substitute
the current comparison or reporting task as the training source.

Local checkpoint sidecars are validated against checkpoint bytes. For an unknown local
reference, `baseline_model.label` and `candidate_model.label` supply independent fallback
names; stored source provenance takes precedence. Missing provenance and missing labels
fail explicitly. An unknown source displays `Training task: unavailable`, without
registering a model. Reports over historical comparison manifests accept `baseline_label`
and `candidate_label` when the manifest and dashboards have no stored identity.

Annotated XLSX dashboards and historical unannotated dashboards are readable through
project adapters that expose the original metric layout. Threshold recovery keeps its
ordered source selection, class labels and available precision; banners are not metric
rows. Pinned dependencies and existing source tasks/artifacts remain unchanged. The
[publication contract](../../014-evaluation-publication/contracts/publication.md#source-identity-on-new-results)
defines presentation on newly produced reports.
