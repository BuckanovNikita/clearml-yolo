# Evaluation publication, plots and identities

This contract amends the result inventory in
[feature 008](../../008-dataset-clearml-tracking/contracts/publication.md). It describes
required publication behavior; [the feature specification](../spec.md), implementation,
and dated verification establish progress and acceptance separately. Historical tasks,
artifacts and verification records are not rewritten.

## Invocation CSV bundle

An invocation publishes effective ground truth as `gt_csv` and, when it has prediction
contexts, one combined result table as `predicts_csv`. The owner registers durable local
shards while stages run, enriches already registered contexts when evaluation becomes
available, and assembles/uploads each canonical CSV once before artifact/model barriers
and final flush. A pipeline reuses its invocation bundle rather than publishing the same
CSV at each nested stage. Workers never publish; a worker-side reporting call is a no-op.

Ground-truth and train commands register effective ground truth only. Predict registers
ground truth and a not-evaluated prediction context. Metrics/validation enrich evaluated
model/split contexts. Comparison reinference creates separate candidate/baseline contexts,
even when a checkpoint or prediction source was used by an earlier stage.

The combined table retains original input fields and distinguishes ground-truth and
prediction rows with `row_type` (`gt` / `predict`). Source IDs are assigned before preprocessing;
`source_row_id` and `object_id` distinguish identical boxes and repeated indices.
Context/model/split identity identifies which evaluation a row belongs to. Evaluation
status and exclusion reasons retain invalid geometry, suppressed predictions, excluded
duplicate ground truth and background records rather than dropping them from exported
evidence. A header-only prediction input remains a real empty result.

Neutral row statuses are `not_evaluated`, `background`, `excluded`, `TP`, `FP`, `FN`
and `filtered`. Exclusion reasons include `duplicate_ground_truth`,
`prediction_preprocessing`, `confidence_threshold`, `class_not_evaluated` and geometry
failures (`invalid_geometry:<reason>`, where reason is `missing`, `nonnumeric`,
`nonfinite`, `reversed_corners` or `zero_area`).
`prepared_index` records the prepared position where available. Source ID defaults
`gt:<position>` / `pred:<position>` identify input positions; context identity scopes
those source IDs when multiple sources have the same positions.

`confidence_threshold` records the selected class threshold. `is_below_threshold` uses
strict `<`; equality is retained. Ground-truth and unavailable flags are null. JSON match
relationships in `matches_pre_threshold` and `matches_post_threshold` preserve
`match_id`, phase, status, nullable `gt_source_row_id`/`pred_source_row_id` and prepared
`gt_index`/`pred_index`, labels, confidence and IoU. Relationships are replicated at
both available endpoints. Prepared-index-to-source mappings are explicit; joining
by box coordinates is forbidden because identical boxes can represent different objects.

Raw source rows, geometry-valid AP populations and preprocessed fixed-threshold matching
populations remain distinct. Existing invalid-schema and confidence checks still fail.
Invalid prediction geometry is excluded from computation with a warning, retained in the
combined evidence, and all-invalid predictions evaluate as empty. Standalone prediction
does not invent evaluation, thresholds or matches. Predictions outside selected image
populations remain in a distinct `unassigned` context with `outside_selected_splits`;
they are not added to authoritative evaluation populations.

## Required artifacts and command inventory

Names below are ClearML artifact keys; the retained local files keep their producer
formats. Full/DTRK workbooks retain original metrics contents rather than replacing them
with duplicate summary workbooks.

| Command | Required publication |
|---|---|
| ground-truth | `gt_csv` |
| train | `gt_csv`, native best Output Model and native telemetry |
| predict | `gt_csv`, `predicts_csv` with not-evaluated prediction rows |
| metrics / val | `gt_csv`, `predicts_csv`, `metrics_best_confidences_val` when calibrated, `metrics_dashboard_full_SPLIT`, `metrics_dashboard_dtrk_SPLIT`, interactive plots for each evaluated context |
| compare with baseline | `gt_csv`, `predicts_csv`, candidate/baseline full/DTRK dashboards per split, `compare_workbook_SPLIT`, `compare_workbook_SPLIT_excluded`, interactive plots and comparison telemetry |
| compare without automatic baseline | `gt_csv`, `predicts_csv`, candidate full/DTRK dashboards and interactive plots, recorded comparison skip reason |
| report | `report_dev_SPLIT`, `report_business_SPLIT` |
| pipeline | Union of enabled stages, with canonical CSVs assembled once and the three paired comparison/report workbooks preserved |

Comparison dashboard keys are `comparison_candidate_dashboard_full_SPLIT`,
`comparison_candidate_dashboard_dtrk_SPLIT`, `comparison_baseline_dashboard_full_SPLIT`
and `comparison_baseline_dashboard_dtrk_SPLIT`. The paired comparison workbook retains
its `Сравнение` sheet; excluded classes are its `_excluded` CSV. Developer/business
report workbooks retain their existing formats. A missing automatic baseline does not
fabricate baseline metrics, comparison results or paired reports; explicit invalid model
references still fail.

The validation threshold CSV retains full precision. Calibration is on `val` only;
selected train/test splits reuse frozen thresholds. Default evaluation is train/val/test,
explicit requested splits remain authoritative, and a missing requested split fails.
Pipeline comparison remains test; standalone comparison uses its selected split.
Combined metrics exports retain calibration and requested splits, plus any other splits
represented by source predictions. They do not invent contexts for unused GT-only splits.

Configuration/provenance, existing comparison plots, native telemetry and optional
FiftyOne link/local receipt remain. Local diagnostics, manifests, match tables, threshold
and methodology files may still support computation/recovery. New publications exclude
raw prediction artifacts, duplicate `metrics_evaluation_*` summary workbooks, separate
match/threshold/methodology sidecars and skipped-baseline candidate summary workbooks.
Historical artifact-backed recovery follows the
[recovery amendment](../../012-remove-legacy-compatibility/contracts/task-recovery.md).

## Interactive confusion matrices

For each context, four `report_plotly` heatmaps show the exact same post-threshold integer
counts: raw, row-normalized, column-normalized and globally normalized. Rows are true
classes; columns are predicted classes. Preserve producer class order and background;
numeric/Unicode labels remain distinct. Numeric axis positions with explicit label ticks
prevent implicit lexical sorting of numeric-looking class names.

Normalized values use one percentage scale, 0–100, across contexts. Hover identifies true
and predicted labels, exact count and denominator. Zero denominators produce finite zero
values and the explicit text `no observations`. Normalization never changes the raw
payload. The renderer does not rerun matching or derive counts from rounded dashboards.

## Interactive precision–recall curves

Publish one class/context PR plot at IoU 0.50 with recall on X and precision on Y, both
bounded to [0, 1]. Reconstruct the same geometry-valid population, confidence ordering,
matching and precision integration used by authoritative `compute_map`, using public
matching APIs without modifying the pinned dependency. AP50 parity must be checked for
both integration methods, supported matching strategies, confidence ties and empty cases.
Ground truth is the prepared/deduplicated authoritative AP population; original
pre-deduplication GT remains export evidence only. Valid raw predictions precede
prediction preprocessing/NMS and class threshold filtering. Float32 boxes/cumulative arithmetic, sorting and epsilon
follow authoritative computation. PR is not the frozen-threshold confusion-matrix
population.

Display AP50, integration method, class and context/model/split identity. Hover includes
confidence and cumulative TP/FP for each actual observation. Ground truth with no
predictions has an empty curve and AP50 zero. No ground truth means unavailable recall
and AP50, with an annotation and no invented point. Do not overlay an operating point
from a different population and do not publish a PR CSV artifact.

Plot identities encode context/model/split/class components reversibly, so separators,
numeric labels and Unicode cannot overwrite another context. The adapter submits plain
Plotly-compatible dictionaries through the SDK without a new plotting dependency.
ClearML replaces plot titles with series names, so persistent annotations retain
human-readable context and AP/method metadata.

## Experiment and model display names

Unused requested names remain unchanged. Exact project-local task/model name collisions,
including archived records and excluding current IDs, receive a readable adjective–noun
suffix shared by the experiment and its owned best model. Recheck names after writes for
up to 20 attempts; fail if no collision-free result is verified. A cloned invocation
resolves its own fresh display identity. Paths, checkpoint URLs and model IDs remain
stable; display-name resolution does not reroute native outputs.

Owned-model threshold association follows the
[metadata contract](../../008-dataset-clearml-tracking/contracts/model-metadata.md).
Standalone metrics never creates or mutates a model. Calibration provenance identifies
the SHA-256 of the checkpoint actually used for prediction; a caller-provided path alone
is insufficient.

## Failure and verification boundaries

Register expected publications before finalization. Owner callbacks assemble canonical
CSVs before artifact/model barriers and flush. Required assembly, upload, model metadata,
flush or interruption errors fail the command/task and retain local diagnostic evidence.
FiftyOne stays optional under its maintained publisher contract.

Mocked payload tests establish adapter behavior, not native execution, GPU use, uploads
or server readback. Acceptance additionally requires downloaded canonical CSV/dashboard
content, remote plot inspection, model metadata/checkpoint binding verification, CPU/GPU
runs, documentation checks and a fresh independent review. Record commands, observations
and unavailable gates in dated verification evidence.
