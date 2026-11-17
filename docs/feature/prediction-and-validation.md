# Prediction and validation

Prediction runs one trained detector checkpoint over the images of a ground-truth CSV and
writes a canonical prediction table that later stages can score. `cy-predict` produces
only that table; `cy-val` predicts the selected splits and the validation split and then
scores them with the frozen-threshold evaluation of `cy-metrics`. The `cy` pipeline runs
the same prediction stage on the checkpoint it has just trained. Every prediction table
is bound to the checkpoint bytes and the image-naming mode that produced it, so later
stages cannot score a table against the wrong model or the wrong image identities.

## Behavior

### Inputs

- `weights` selects the checkpoint: a local file, a 32-character ClearML task ID (its
  selected best model is downloaded, see [comparison](comparison.md#model-references)),
  or a `clearml://<model id>` reference whose stored SHA-256 must match the download.
  `ultralytics_predict.model` is an alternative for YOLO; setting both to different
  checkpoints fails with `weights conflicts with ultralytics_predict.model`. In the `cy`
  pipeline the trained checkpoint owns inference. A string naming an existing local file
  is used as that file, without any library cache lookup.
- `ground_truth` is a CSV path or ClearML dataset selector
  ([datasets and ground truth](datasets-and-ground-truth.md)). Images come from its
  `image_path` column; a native `source` setting is rejected.
- `splits` restricts prediction to the named splits; each split is inferred as a
  separate group so test batches are reproducible. `null` predicts every image once.
- The checkpoint identity comes from its recorded source (task, model, training task,
  SHA-256). A checkpoint without recorded provenance requires `model_label`; otherwise
  the command fails with `Model provenance is unavailable; supply a custom model_label`.

### Prediction table

The CSV has exactly the columns `image_name`, `instance_label`, `confidence`,
`bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`, with boxes in original-image pixel
coordinates and exact class strings from the checkpoint vocabulary. Images without
detections contribute no rows; an empty result still has the full header. `image_name`
follows `image_name`: `name` (basename, default), `stem` or `path` (the caller's spelling
of the image path). Only `name` can be evaluated or compared; `stem` and `path` are raw
export modes.

Every requested image must yield a native result. An image the backend cannot decode or
does not score fails the invocation instead of silently shrinking the scored set.

### Provenance sidecar

Next to the CSV, `<predictions>.csv.provenance.json` records the SHA-256 of the
prediction bytes, `prediction_image_name`, the checkpoint SHA-256 and the model
identity. Readers (`cy-metrics`, comparison cache reuse) accept the sidecar only when
the prediction bytes still match; a stale, malformed or contradictory sidecar fails. A
missing sidecar is accepted only when every prediction `image_name` is a canonical
ground-truth basename. If the checkpoint file changes while predicting, the command
fails with `Checkpoint changed while producing predictions`.

### Native settings and quiet output

Prediction executes only its resolved group (`ultralytics_predict` for YOLO,
`model.predict` for other families). YOLO prediction defaults are `conf=0.001`,
`batch=1`, `rect=true`, `save=false`, `verbose=false` and `device=[-1]` (Ultralytics
chooses the device), and it inherits applicable training values such as `imgsz=960` and
`nms=true`; `conf` is a raw
filtering threshold, separate from calibrated class thresholds. Native per-image output
is suppressed; one rate-limited progress indicator reports inference on every backend.
The requested settings are written as `ultralytics_predict_requested.yaml` and the
effective settings as `ultralytics_predict.yaml`; split groups after the first add their
zero-based index (`ultralytics_predict_<n>.yaml`,
`ultralytics_predict_<n>_requested.yaml`). Image manifests are written under
`prediction_inputs/<n>/images.txt` and native output under `native/predict` beside the
CSV. Native normalization (for example stride-aligned `imgsz`) is recorded in the run
configuration as `prediction_result.native_normalization`, separate from the request.

### Native prediction controls

Other families read these `model.predict` keys; unknown keys are rejected.

| Key | Default | Meaning |
| --- | --- | --- |
| `device`, `batch` | `null`, 1 | Device (`null` lets the family decide) and batch size |
| `imgsz` | `null` | `null` uses the checkpoint's preprocessing size |
| `conf`, `iou`, `max_det` | 0.001, 0.7, 300 | Score filter, NMS IoU and detection limit |
| `half` | `false` | Faster R-CNN/FCOS CUDA autocast |

DEIMv2 and RF-DETR reject a nondefault `iou` and `half=true` (`RF-DETR nondefault iou
and half controls are unsupported`, likewise for DEIMv2); their size rules are in
[detector families](detector-families.md). Faster R-CNN and FCOS accept rectangular
sizes, round each dimension up to a multiple of 32 keeping the aspect ratio, and pad on
the right and bottom. Effective sizes are recorded and can differ between families.

### Validation (`cy-val`)

`cy-val` predicts `val` plus the requested splits (default `[train, val, test]`) into
`<output_dir>/predictions.csv`, then calibrates thresholds on `val` and scores each
requested split under `<output_dir>/metrics` exactly as
[evaluation metrics](evaluation-metrics.md) describes. It declares both the `predict`
and `metrics` result producers on one ClearML task. Validation never trains; the
splits come from the ground-truth CSV, and `val` and `test` must not share an image.

### Geometry filtering before scoring

Scoring stages filter malformed prediction geometry only in an in-memory evaluation
copy; the prediction CSV is never rewritten, and published prediction rows keep finite
zero-area boxes produced by native clipping. Each row is dropped for the first matching
reason: `missing`, `nonnumeric`, `nonfinite`, `reversed_corners`, `zero_area`. One
warning per frame reports the total, the count per reason and up to five image names.
All-invalid predictions score as empty predictions, so every ground-truth box becomes a
false negative. Missing required columns, invalid confidence or label values and
unknown image identities remain fatal and are not hidden by the geometry filter.

## Configuration

| Option | Commands | Default | Meaning |
| --- | --- | --- | --- |
| `weights` | both | `null` | Checkpoint path, task ID or `clearml://` model |
| `ground_truth` | both | required | CSV path or dataset selector |
| `splits` | `cy-predict` | `null` | Splits to predict; `null` predicts every image |
| `splits` | `cy-val` | `[train, val, test]` | Splits to score; `val` is always predicted |
| `image_name` | `cy-predict` | `name` | `name`, `stem` or `path` |
| `output` | `cy-predict` | `null` | CSV path; `null` uses the task run directory |
| `output_dir` | `cy-val` | `null` | Destination for predictions and metrics |
| `model_label` | both | `null` | Display name for checkpoints without provenance |
| `evaluation.*` | `cy-val` | see below | Scoring rules |

`evaluation.*` options are listed in [evaluation metrics](evaluation-metrics.md).
YOLO prediction settings are described in
[commands and configuration](commands-and-configuration.md); other families use the
native prediction controls above. FiftyOne publication from `cy-predict` is
optional ([FiftyOne publication](fiftyone-publication.md)); `cy-val` disables it.

## Failure behavior

- No checkpoint: `Prediction requires weights=<checkpoint> or ultralytics_predict.model`.
- A requested split absent from the ground truth: `No ground-truth rows for splits [...]`;
  no images at all: `No images to predict`.
- Unknown `image_name` mode, a non-detection checkpoint, a native `source`, an AutoBatch
  prediction `batch` (`-1`), or an image without a native result fails before any table
  is written.
- Scoring a `stem` or `path` table fails with
  `Comparison and evaluation require image_name='name'`; prediction names outside the
  ground-truth membership fail before filtering.
- A checkpoint without provenance and without `model_label` fails before inference.
- Standalone commands fail on any computation or required publication error and keep
  their local output ([ClearML publication](clearml-publication.md)).

## Limits

- The re-inference cache used by comparison is a separate mechanism; see
  [comparison](comparison.md#re-inference-and-prediction-cache).
- `image_name=name` requires basenames to be unique within the scored ground truth.
- The provenance sidecar binds bytes, not file locations: moving the CSV without its
  sidecar loses the naming mode and source identity.

## Code and tests

- [`application/use_cases/predict.py`](../../src/clearml_yolo/application/use_cases/predict.py)
  and [`val.py`](../../src/clearml_yolo/application/use_cases/val.py): stage workflows.
- [`adapters/yolo/inference.py`](../../src/clearml_yolo/adapters/yolo/inference.py),
  [`adapters/torchvision/inference.py`](../../src/clearml_yolo/adapters/torchvision/inference.py),
  [`adapters/integrations/detectors.py`](../../src/clearml_yolo/adapters/integrations/detectors.py):
  native inference and family routing.
- [`adapters/clearml/results.py`](../../src/clearml_yolo/adapters/clearml/results.py):
  provenance sidecar.
- [`adapters/evaluation/scoring.py`](../../src/clearml_yolo/adapters/evaluation/scoring.py):
  geometry filter.
- Tests: [`test_predict.py`](../../tests/test_predict.py),
  [`test_inference.py`](../../tests/test_inference.py),
  [`test_prediction_geometry.py`](../../tests/test_prediction_geometry.py),
  [`test_quiet_prediction.py`](../../tests/test_quiet_prediction.py),
  [`test_invalid_prediction_workflows.py`](../../tests/test_invalid_prediction_workflows.py).
- Offline tests use fake native predictors; native GPU inference is established only by
  the live suite.
