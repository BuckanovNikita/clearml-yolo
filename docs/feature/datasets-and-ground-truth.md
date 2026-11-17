# Datasets and ground truth

Every CY experiment reads its annotations from one ground-truth CSV: one row per object
(or one background row per image without objects) with the image name, image path, class
label, pixel box corners and split. The `ground_truth` setting of `cy`, `cy-train`,
`cy-predict`, `cy-val`, `cy-metrics`, `cy-compare` and `cy-export` accepts a local CSV
path or a reference to a finalized ClearML dataset that holds only that CSV.
`cy-ground-truth` converts a YOLO `data.yaml` dataset into this CSV. Training validates
the CSV, drops invalid boxes, and prepares a native working copy (NDJSON, flat YOLO or
COCO) in a shared cache that is reused while the CSV and its image references stay the
same.

## Behavior

### Ground-truth sources

```yaml
ground_truth: annotations/truth.csv
ground_truth: {dataset_id: DATASET_ID}
ground_truth: {project_name: annotations, name: ground-truth}
ground_truth: {project_name: annotations, name: ground-truth, version: "1.2.0"}
```

On the command line a mapping is one quoted override, for example
`'ground_truth={project_name:annotations,name:ground-truth,version:"1.2.0"}'`.
`project_name` names the dataset project, independently of `clearml.project_name`. The
selector is validated before any lookup. The invocation resolves it once and passes the
resolved CSV to every nested stage. A local path is used as is and produces one warning,
`Using local ground-truth CSV <path>; prefer a ClearML dataset reference for versioned
annotations.`; nested stages and derived CSVs do not warn again. The warning comes from
resolution at execution, so queue submission never emits it.

A dataset reference requires a completed, finalized ClearML dataset whose current
inventory is exactly the root file `dataset.csv`. The CSV is downloaded through the
ClearML SDK cache without soft links and is used unchanged: no image conversion, upload
or path remapping. Without `version`, the ClearML SDK selects the latest version (highest
semantic version, otherwise most recently updated), so a later invocation can resolve a
newer version; a dataset ID or an explicit version pins the source. The task records the
requested selector and, separately, the resolved dataset ID, project, name, version and
CSV SHA-256 under `ground_truth_source` in `run`. Help, configuration export and queue
submission download nothing; Agent replay and queued execution resolve the original
selector again.

### CSV interpretation

Required columns are `image_name`, `image_path`, `instance_label`, `bbox_x_tl`,
`bbox_y_tl`, `bbox_x_br`, `bbox_y_br` and `split`; other columns are allowed. The file is
UTF-8 (a BOM is accepted). Identity columns are read as literal text: `NA`, `NULL`,
`nan`, `None`, numeric-looking (`0001`) and Unicode values stay distinct strings; only
empty cells are missing. Row order and round-trip float precision are kept.

- `image_path` resolves against the CSV's own directory (for a ClearML dataset, the
  downloaded CSV's directory), never the launch directory; absolute paths stay absolute.
  Images must be readable by the executing process at those paths.
- `image_name` must equal the basename of the resolved path. One name maps to one path
  and one split, and one path to one name.
- `split` is `train`, `val` or `test`.
- A background row has an empty label and four empty coordinates; an image cannot mix
  background and annotation rows.
- Coordinates are absolute pixels: top-left and bottom-right corners.
- Class indices follow the sorted set of distinct labels; labels keep their exact text.

### Training validation and preparation

Training reads every image once to obtain its size (JPEG EXIF orientations 6 and 8 swap
width and height). A box is invalid when its label is empty, a coordinate is missing,
non-numeric or non-finite, its width or height is not positive, or it leaves the image.
Invalid boxes are dropped and counted (`Invalid bounding boxes dropped: N`), an image
whose boxes were all dropped is kept, and a warning names each class without a valid
training example. The cleaned `ground_truth.csv` feeds every later pipeline stage and is
published once as `gt_csv` ([clearml-publication](clearml-publication.md)).

The CSV owns dataset membership and class meaning. CY forces the native settings `task`,
`classes`, `data`, `single_cls`, `fraction`, `cls_remap` and `split`, logs each change and
records them as `training_data_overrides`. `dataset_format=ndjson` (default) or `flat`
prepares YOLO data; other detector families always use COCO. Source images are copied,
never modified, and are not uploaded as dataset artifacts. A prepared entry contains
`data.yaml`, `ground_truth.csv`, `preparation.json` (counts, invalid boxes, image
inventory), `labels.zip`, `completion.json` and, for NDJSON, `dataset.ndjson`.

### Dataset cache

Prepared entries live in `dataset_cache_dir`, by default
`CY_HOME/.cache/clearml-yolo/datasets` (independent of XDG settings). The entry key
hashes the CSV bytes, the ordered resolved image references, the format and the
preparation version. Identical absolute references reuse one entry across CSV
locations; relative references that resolve to different images never collide. A hit
reads no image contents or modification times and copies nothing. Each consumer holds a
native file lock in `.locks/` while it uses the entry, so concurrent requests build an
entry once. Training records `run.prepared_dataset={cache_identity, root}`. Changing image
bytes at an unchanged path is not detected: invalidate the entry explicitly while the
cache is idle.

### YOLO conversion with `cy-ground-truth`

`cy-ground-truth data_yaml=data.yaml` reads the dataset through Ultralytics' own
resolution. Split entries may be image directories or `.txt` image lists. Label lines
must have five fields (`class cx cy w h`), finite normalized values within
`[-0.01, 1.01]`, positive sizes and a class index defined in `names`; boxes are converted
to pixels with EXIF-aware sizes and clipped to the image. Images without labels become
background rows. When the dataset has no `test` images, `test_fraction` of the `val`
images (by image name, seeded by `seed`, keeping at least one `val` image) become `test`.
The CSV is written to `output`, by default `ground_truth.csv` in the task's run root, is
published as `gt_csv`, and `data.yaml` is attached as the `dataset` configuration.

## Configuration

| Setting | Default | Commands |
| --- | --- | --- |
| `ground_truth` | required (`???`); `null` for `cy-export` | experiment commands |
| `dataset_format` | `ndjson` | `cy`, `cy-train` |
| `dataset_cache_dir` | `null` (`CY_HOME/.cache/clearml-yolo/datasets`) | `cy`, `cy-train` |
| `required_splits` | `null` (`train` and `val`) | `cy-train` |
| `data_yaml`, `output` | required, `null` | `cy-ground-truth` |
| `test_fraction`, `seed` | `0.5`, `0` | `cy-ground-truth` |

`cy-export` permits absent ground truth unless verification needs a labeled corpus.

## Failure behavior

- Selectors fail before lookup: `dataset_id cannot be combined with project_name, name or
  version`, `Ground truth requires dataset_id or both project_name and name`, `Dataset
  selector values must not be empty`; unknown fields and non-string values (an unquoted
  version) are rejected. An empty path fails with `Ground truth path must not be empty`.
- Lookup never creates a dataset. An unfinalized dataset, a missing root `dataset.csv`,
  extra files or links (`must contain only root dataset.csv; store images and other files
  outside the dataset`) and download failures fail before the CSV is used.
- The CSV fails with file and row context for duplicate or missing headers, no data rows,
  empty `image_name` or `image_path`, an invalid split, a name/basename mismatch,
  conflicting name, path or split ownership, mixed or duplicate background rows,
  numerically duplicate boxes, unsupported extensions or decoded formats, unreadable
  images and images smaller than 10 x 10 pixels.
- Training fails when a required split has no images or no valid training box remains,
  for `task` other than `detect` and for `resume` (`resume is unsupported with
  ground_truth; use model weights to fine-tune`). NDJSON preparation fails on
  case-insensitive label-stem collisions within a split.
- A cache entry that exists but does not validate is preserved and reported: `Dataset
  cache entry is invalid and has been preserved: <entry>. Inspect it and explicitly
  repair or remove it while the cache is idle.` A failed build removes only its own
  staging directory. A platform without native file locks, or a lock that cannot be
  acquired, fails without a soft-lock fallback.
- `dataset_cache_dir` inside the pipeline run directory or the training project fails.
- `cy-ground-truth` fails for segment labels, unknown class indices, non-positive or
  out-of-range coordinates, a `test_fraction` outside `[0, 1)`, missing split entries,
  a dataset with no images, and one image name used by different files.

## Limits

- CSV ground truth is the only training input; native dataset paths cannot replace it.
- A ClearML dataset holds only the CSV; images must be reachable at the CSV's paths. The
  SDK may still fetch whole historical archive chunks, including media removed from an
  inherited dataset; use a fresh CSV-only lineage to avoid that transfer.
- The cache never deletes entries; repair and removal are manual idle maintenance.

## Code and tests

- [application/ground_truth.py](../../src/clearml_yolo/application/ground_truth.py) —
  selector validation, single resolution, local warning
- [adapters/clearml/datasets.py](../../src/clearml_yolo/adapters/clearml/datasets.py) —
  ClearML dataset lookup and CSV digest
- [adapters/storage/dataset_records.py](../../src/clearml_yolo/adapters/storage/dataset_records.py),
  [core/datasets.py](../../src/clearml_yolo/core/datasets.py) — CSV and box validation
- [adapters/storage/file_io.py](../../src/clearml_yolo/adapters/storage/file_io.py) —
  literal CSV reading and media resolution
- [adapters/storage/dataset.py](../../src/clearml_yolo/adapters/storage/dataset.py),
  [dataset_export.py](../../src/clearml_yolo/adapters/storage/dataset_export.py),
  [dataset_cache.py](../../src/clearml_yolo/adapters/storage/dataset_cache.py) —
  preparation and cache
- [adapters/yolo/ground_truth.py](../../src/clearml_yolo/adapters/yolo/ground_truth.py) —
  `cy-ground-truth` conversion
- Tests: [test_ground_truth_sources.py](../../tests/test_ground_truth_sources.py),
  [test_dataset_records.py](../../tests/test_dataset_records.py),
  [test_input_correctness.py](../../tests/test_input_correctness.py),
  [test_dataset.py](../../tests/test_dataset.py),
  [test_dataset_export.py](../../tests/test_dataset_export.py),
  [test_dataset_cache.py](../../tests/test_dataset_cache.py),
  [test_ground_truth.py](../../tests/test_ground_truth.py)
- ClearML dataset lookup is tested only against a simulated SDK; the live suite uses a
  local CSV, so no automated test downloads a real ClearML dataset.
