# Comparison

Comparison decides whether a candidate model is better than a baseline by running both
checkpoints again on the same current images and scoring each at its own frozen
validation thresholds. `cy-compare` compares two model references on one split (`test`
by default); the `cy` pipeline compares its freshly trained checkpoint on `test` against
the latest promoted model. Stored metrics, dashboards or predictions of historical runs
never replace current re-inference. The result is a paired statistical workbook and a
manifest that [reports](reports.md) turns into developer and business workbooks.

## Behavior

### Model references

`baseline_model` and `candidate_model` are model references with these fields. Inside
`cy` only `compare.baseline_model` is configurable; the candidate is the model the
pipeline has just produced: its own task's best model after training, or the predicted
checkpoint with this run's validation thresholds when `skip_train=true`.

| Field | Default | Rule |
| --- | --- | --- |
| `source` | `clearml` | `clearml` or `local` |
| `task_id` | `null` | Exact ClearML task; not allowed with `local` |
| `project_name` | `null` | Lookup project; `null` uses `clearml.project_name` |
| `task_name` | `null` | Regular expression that must match the whole task name |
| `tags` | `[prod]` | Every tag must be present on the task |
| `weights` | `null` | Required for `local`, rejected for `clearml` |
| `thresholds` | `null` | Class thresholds in `[0, 1]`; nonempty for `local` |
| `label` | `null` | Display name; required when the checkpoint has no provenance |
| `backend`, `preset` | `null` | Set together; describe or assert the detector family |
| `class_names` | `null` | Ordered foreground classes of raw weights |
| `preprocessing` | `null` | Image preparation of raw weights |
| `source_dir` | `null` | DEIMv2 source checkout |

`class_names`, `preprocessing` and `source_dir` require `backend` and `preset`.

A `clearml` reference without `task_id` selects the most recently completed (or
published) task in the project that carries every tag and matches `task_name`; for the
baseline the current task is excluded. A baseline reference whose `source`, `task_id`,
`project_name`, `task_name`, `weights` and `tags` are at their defaults is the automatic
baseline (the latest completed `prod` task); other fields such as `label` or
`thresholds` may still be set.

Each side resolves independently, so YOLO and native families can be compared. Raw
native weights without an embedded descriptor need `backend`, `preset`, the ordered
foreground `class_names` and `preprocessing`; when a descriptor exists, the assertions
must agree with it. Assertions never convert an incompatible architecture. A DEIMv2
reference prepares its verified source even when another family is selected, and an
explicit `source_dir` must pass checkout validation. Checkpoints without detector
metadata and without assertions use YOLO routing.

### Recovering historical models

For a ClearML task, one selection supplies both weights and provenance:

1. When the task has Output Models: the unique model marked best, else the unique model
   named `best.pt`, `best.pth` or `best.ckpt`, else the last registered model with a
   warning. Several candidates at one step fail; artifacts are never used then.
2. Without Output Models: the first present artifact of `train_weights_best.pt`,
   `.pth`, `.ckpt`, `train_weights_best`, `best.pt`, `.pth`, `.ckpt`, `best`, `model`,
   `checkpoint`, then other `.pt`, `.pth` or `.ckpt` artifacts in name order.

Only the selected source is downloaded. Its SHA-256 must match the recorded checkpoint
hash, and a recorded training task must agree with the model's original task. `.pth` and
`.ckpt` files need an embedded descriptor or explicit assertions. Provenance names the
source task and model, or task and artifact; no model link is invented for an artifact.
Source tasks are never modified, and loading an obsolete architecture is not guaranteed.

Explicit `thresholds` win. Otherwise the first present artifact supplies them, in this
order: `metrics_best_confidences_val`, `best_confidences_val`,
`metrics_best_confidences_test`, `best_confidences_test`, `metrics_dashboard_full_val`,
`dashboard_full_val`, `metrics_dashboard_full_test`, `dashboard_full_test`. Threshold
artifacts may be JSON mappings, Series or DataFrames, or CSV/CSV.GZ files; dashboards
may be frames or CSV/CSV.GZ/XLSX with a `confidence` column. Class names stay exact
strings and precision is kept. A dashboard source logs a warning that values may be
rounded and calibration provenance is unavailable.

### Re-inference and prediction cache

Both checkpoints predict the current images of the comparison split from the current
ground truth, on one shared device, with one shared set of inference settings taken from
`ultralytics_predict` or `model.predict` (`conf`, `iou`, `imgsz`, `batch`, `device` and
other native keys). The candidate's requested `imgsz` applies to both; a baseline trained
at another size logs a warning. Every image of the split must exist on disk.

Predictions are cached in `output_dir` as
`<role>_predictions_<split>_<digest>.csv`. The digest covers the checkpoint path and
SHA-256, the shared inference settings, the raw-checkpoint assertions and the split's
image names and resolved paths (image bytes are not hashed). With
`inference.reuse_existing=true` a cache file is reused only when its `.metadata.json`
evidence is valid, its native output lies under the comparison directory and its image
manifest still exists; otherwise inference runs again. A cache whose provenance sidecar
names another checkpoint or model identity fails. Cache files are written atomically.

### Scoring and statistics

Each side is scored as in [evaluation metrics](evaluation-metrics.md) with its own
thresholds. Displayed classes are the union of both model vocabularies and the scored
classes; a class one model cannot predict keeps the other model's metrics and shows
`NA` for the missing side. A class is excluded from statistics with a reason when it is
unknown to one or both models (`Только в новой модели`, `Только в прод модели`,
`Нет ни в одной модели`), has no ground truth in the split (`Нет разметки в сплите`) or
no predictions from either model (`Ни одна модель не предсказала класс`).

For each eligible class, precision is tested with an image-level bootstrap and recall
with an exact two-sided McNemar test (a bootstrap supplies its interval). Deltas are
`candidate - baseline`. Benjamini–Hochberg correction spans every precision and recall
hypothesis of the split; untestable hypotheses stay out of the family. Verdicts are
`improved`, `degraded`, `not_significant` or `unavailable`. A pooled row over the
shared eligible classes is judged on its raw p-values outside the family. Without
shared eligible classes the pooled comparison is unavailable while per-model metrics
remain.

### Outputs

`compare_workbook_<split>.xlsx` (sheet `Сравнение`, plus `Dataset counts`), sibling
`_excluded.csv` and `_methodology.csv`, `comparison_manifest.json` (split, dashboards,
prediction files, identities), per-role dashboards and native YAML. ClearML receives
the workbook, the excluded-class table, both role dashboards and headline single values
(`degraded_*`, `improved_*`, `classes_tested`, `classes_excluded`, `pooled_delta_*`).
Baseline charts and comparison tables never appear in Plots. Each side's original
training counts appear in `Dataset counts` as described in
[reports](reports.md#training-counts-and-warnings).

### Missing automatic baseline

When the automatic baseline finds no task, the candidate is still re-inferred and
scored, its dashboards and plots are published, a candidate-only workbook
`compare_evaluation_candidate_<split>.xlsx` (`Classes`, `Summary`, `Dataset counts`) is
written with sibling `_thresholds.csv` and `_methodology.csv`, the `skipped` status and
reason are recorded in that methodology file and as `comparison_status` in the run
configuration, and no paired results are fabricated. The pipeline then skips its
report stage.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `baseline_model`, `candidate_model` | automatic `prod` lookup | Model references |
| `ground_truth` | required | CSV path or dataset selector |
| `split` | `test` | Comparison split; the pipeline always uses `test` |
| `output_dir` | task-owned route | Destination |
| `inference.reuse_existing` | `true` | Reuse a valid prediction cache |
| `inference.image_name` | `name` | Only `name` is accepted |
| `q` | `0.05` | False-discovery level, finite within `[0, 1]` |
| `bootstrap_iterations` | `10000` | Positive integer |
| `seed` | `0` | Bootstrap seed |
| `evaluation.*` | see [evaluation metrics](evaluation-metrics.md) | Applied to both sides |

Prediction `model`, `project` and `name` are owned by comparison and fail when set.

## Failure behavior

- An explicit reference that finds no task, or any invalid reference, fails; only the
  automatic baseline may be absent.
- Both sides resolving to the same checkpoint file fails with
  `Both sides resolved to the same checkpoint`; two references that bind conflicting
  metadata to one checkpoint fail with `Conflicting model metadata for the same checkpoint`.
- A present but malformed or undownloadable threshold or checkpoint source fails without
  trying a later source; so do empty or duplicate classes and out-of-range confidences.
- Ambiguous best models, a hash mismatch or a training-task disagreement fails.
- A missing image, an empty split, or a model reference without provenance or `label`
  fails before scoring.
- Native keys under `inference` fail with `Unsupported inference settings: [...]`; shared
  inference settings belong in `ultralytics_predict` or `model.predict`.
- When a native-family side receives YOLO prediction settings, a changed key it cannot
  honor (for example `classes`) fails with `Unsupported native detector prediction
  setting: <key>`, and `conf=null` fails with `Native detector comparisons require an
  explicit confidence threshold`.

## Limits

- Image content is not hashed for the cache: images are immutable at unchanged paths.
- Current comparison settings always apply; source task configurations are not imported.
- Statistics describe the current split only; historical metrics are never mixed in.

## Code and tests

- [`application/use_cases/compare.py`](../../src/clearml_yolo/application/use_cases/compare.py):
  workflow, references, cache key, skip.
- [`core/comparison/`](../../src/clearml_yolo/core/comparison/): rows, eligibility, BH
  family; [`adapters/evaluation/comparison.py`](../../src/clearml_yolo/adapters/evaluation/comparison.py):
  shared statistics.
- [`adapters/clearml/models.py`](../../src/clearml_yolo/adapters/clearml/models.py):
  task lookup, model and threshold recovery;
  [`adapters/yolo/reinfer.py`](../../src/clearml_yolo/adapters/yolo/reinfer.py): cache.
- Tests: [`test_comparison_assemble.py`](../../tests/test_comparison_assemble.py),
  [`test_comparison_reinfer.py`](../../tests/test_comparison_reinfer.py),
  [`test_comparison_recovery.py`](../../tests/test_comparison_recovery.py),
  [`test_comparison_significance.py`](../../tests/test_comparison_significance.py),
  [`test_comparison_identity_cache.py`](../../tests/test_comparison_identity_cache.py),
  [`test_shared_comparison.py`](../../tests/test_shared_comparison.py),
  [`test_clearml_report.py`](../../tests/test_clearml_report.py).
- ClearML lookup and download are exercised with SDK fakes; real recovery is
  established only by the live suite.
