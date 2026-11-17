# Evaluation metrics

Evaluation scores a prediction table against ground truth at confidence thresholds that
are calibrated once on the validation split and then frozen. `cy-metrics` evaluates an
existing prediction CSV; `cy-val` and the `cy` pipeline run the same evaluation after
their own prediction stage, and `cy-compare` reuses it for both models at their own
frozen thresholds. Each evaluated split yields exact per-class metrics, readable
dashboards and row-level results that keep every original object and prediction
traceable to its source row.

## Behavior

### Order of work

1. Read the prediction and ground-truth CSVs lexically and give every row a stable
   `source_row_id` (and `object_id`) before any filtering.
2. Check that every requested split and `val` exist, that no image belongs to both `val`
   and `test`, and that every prediction `image_name` is a canonical ground-truth
   basename (see [prediction and validation](prediction-and-validation.md)).
3. Prepare ground truth (duplicate boxes removed only when `evaluation.preprocess=true`),
   filter invalid prediction geometry in memory, then apply prediction preprocessing:
   each of `evaluation.preprocess_preds_conf_threshold`,
   `evaluation.preprocess_preds_nms_containment_threshold` and
   `evaluation.preprocess_preds_nms_iou_threshold` filters only when it is not `null`.
4. Take the class vocabulary as ground-truth labels plus predicted labels; prediction-only
   classes stay in scoring and count as false positives.
5. Calibrate thresholds on `val` once: `confidence_optimization=per_class` solves one
   threshold per class, `global` one shared threshold.
6. Score every requested split (default `[train, val, test]`) at those frozen thresholds.

### Two prediction populations

Fixed-threshold matching (TP, FP, FN, confusion counts, per-image outcomes) uses the
prepared predictions. Average precision and precision-recall observations use the
geometry-valid predictions before preprocessing, so low-confidence and NMS-suppressed
boxes still contribute to AP. Both come from one call into the shared scientific
library; the reconstructed AP50 of every class with ground truth must equal the
library's authoritative AP50, otherwise evaluation fails.

### Shared library

The pinned `digital-metrics` dependency computes box matching (`greedy`, `hungarian`,
`iou_prior`), the threshold search, fixed-threshold metrics, AP integration (`interp`
or `continuous`), confusion counts, PR observations, headline summaries and the
dashboard renderer. The application owns calibration scheduling, frozen thresholds,
split selection, vocabulary, ground-truth deduplication, model identity and source-row
lineage. Metrics are never derived by re-reading rendered reports.

### Metric values

Per class: `tp`, `fp`, `fn`, `confidence`, `ap50`, `ap75`, `ap50_95`, `precision`,
`recall`, `f1_score`, `perebrak` (`1 - precision`), `nedobrak` (`1 - recall`) and
the lower/upper confidence bounds of precision, recall, `perebrak` and `nedobrak`.
Float values keep full precision; unavailable values stay unavailable rather than zero.
A class with ground truth and no predictions has AP50 zero; a class without ground
truth has unavailable recall and AP.

### Thresholds

Thresholds are exact floats in `[0, 1]` for every required class. They are written to
`metrics_best_confidences_val.csv` (`class_name`, `confidence`, 17 significant digits)
and published under that name. In the `cy` pipeline the invocation-owned best model also
receives them as metadata after its checkpoint hash matches the prediction provenance
([ClearML publication](clearml-publication.md)); standalone `cy-metrics` never creates
or changes a model. Test data never calibrates.

### Outputs per split

In `output_dir`: `full_dashboard_<split>.xlsx`, `метрики_дтрк_<split>.xlsx`,
`matrix_<split>.xlsx`, four freshly generated plots
`<metric>_confidence_intervals_<split>.png` for `recall`, `precision`, `perebrak` and
`nedobrak` (existing plots with these names, with or without the split suffix, are
removed first; other files stay), `evaluation_<split>.json` (methodology, boxes,
matches and the AP/PR report) and `metrics_evaluation_<split>.xlsx` (`summary`,
`per_class`, `confusion_matrix`, `Dataset counts`) with sibling CSVs
`_ground_truth_matches`, `_prediction_matches`, `_thresholds` and `_methodology`.
Workbook layout, footers and charts are described in [reports](reports.md). Split
names are percent-encoded in file names and unchanged in content.

### Result rows

Every source row appears once per evaluated context with `row_type` (`gt` or
`predict`), its split and model context, and `evaluation_status`:

| Status | Meaning |
| --- | --- |
| `TP`, `FP`, `FN` | Outcome at the frozen threshold |
| `background` | Ground-truth row of an empty image |
| `filtered` | Prediction below its class threshold (`confidence_threshold`) |
| `excluded` | Not scored; `exclusion_reason` says why (see below) |
| `not_evaluated` | Prediction-only context; no thresholds or matches are invented |

Exclusion reasons are `invalid_geometry:<reason>`, `duplicate_ground_truth`,
`prediction_preprocessing` and `class_not_evaluated` (no threshold for the class).
Predictions carry `confidence_threshold` and `is_below_threshold` (strict `<`, so a
confidence equal to the threshold passes). `matches_pre_threshold` and
`matches_post_threshold` hold JSON match records with prepared indices, labels,
confidence and IoU; prepared indices map to `source_row_id`, never to box coordinates.
Prediction images outside the selected splits form an `unassigned` context with
`outside_selected_splits` and never enter the scoring population.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `predictions` | required (`cy-metrics`) | Prediction CSV to score |
| `ground_truth` | required | CSV path or dataset selector |
| `splits` | `[train, val, test]` | Splits to score, in order |
| `calibration_split` | `val` | Must be `val` |
| `model_label` | `null` | Display name when the CSV has no provenance |
| `evaluation.iou_threshold` | `0.5` | Finite, within `[0, 1]` |
| `evaluation.matching_strategy` | `iou_prior` | `greedy`, `hungarian`, `iou_prior` |
| `evaluation.ap_method` | `interp` | `interp` or `continuous` |
| `evaluation.confidence_optimization` | `per_class` | `per_class` or `global` |
| `evaluation.skip_cohen_kappa` | `true` | Must stay `true` |
| `evaluation.preprocess` | `false` | Remove duplicate ground-truth boxes |
| `evaluation.preprocess_preds_*` | `null` | Optional prediction confidence/NMS filters |
| `evaluation.backend` | `null` | Must stay `null` |

`output_dir` defaults to a task-owned route. FiftyOne publication is optional.

## Failure behavior

- `calibration_split` other than `val`, `splits` containing `all`, a missing requested
  split, missing `val`, or an image in both `val` and `test` fails before scoring.
- `evaluation.backend` set, or `evaluation.skip_cohen_kappa=false`, fails.
- When neither ground truth nor predictions carry any class label, evaluation fails with
  `Ground truth contains no labelled objects to evaluate`.
- Thresholds missing a required class, non-finite or outside `[0, 1]` fail.
- Non-canonical or unknown prediction names, stale provenance and schema or confidence
  errors fail; invalid geometry alone does not.
- A missing dashboard, plot or reconstructed-AP mismatch fails the split.
- Computation and required-publication errors fail the standalone command and keep local
  output; inside a pipeline with successful training they become warning completion.

## Limits

- Calibration is fixed to `val`; there is no test-calibrated or cross-validated mode.
- Cohen's kappa is not computed.
- Prediction preprocessing thresholds change the fixed-threshold population only; AP uses
  the geometry-valid predictions regardless.

## Code and tests

- [`application/use_cases/metrics.py`](../../src/clearml_yolo/application/use_cases/metrics.py),
  [`application/evaluation.py`](../../src/clearml_yolo/application/evaluation.py): workflow.
- [`adapters/evaluation/scoring.py`](../../src/clearml_yolo/adapters/evaluation/scoring.py):
  calibration and fixed-threshold evaluation over `digital-metrics`.
- [`core/evaluation/`](../../src/clearml_yolo/core/evaluation/): policy, models, payload and
  result rows; [`core/validation/`](../../src/clearml_yolo/core/validation/): schemas.
- Tests: [`test_metrics.py`](../../tests/test_metrics.py),
  [`test_scoring_evidence.py`](../../tests/test_scoring_evidence.py),
  [`test_pr_curves.py`](../../tests/test_pr_curves.py),
  [`test_calibration_metadata.py`](../../tests/test_calibration_metadata.py),
  [`test_quality_properties.py`](../../tests/test_quality_properties.py),
  [`test_evaluation_payload.py`](../../tests/test_evaluation_payload.py),
  [`test_evaluation_separation.py`](../../tests/test_evaluation_separation.py).
- These checks establish offline numerical behavior; they do not measure model accuracy
  or remote publication.
