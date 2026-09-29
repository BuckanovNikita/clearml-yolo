# Dataset Preparation Data Model

## Canonical Records

- `Box`: class `label` and pixel corners `x1`, `y1`, `x2`, `y2` (floats).
- `ImageRecord`: `name`, absolute `path`, positive integer `width`/`height`, `split`
  (`train`, `val`, or `test`), and list of valid `boxes`.
- `InvalidBox`: one-based CSV `row` number including the header, `image_name`, and `reason`.
  One attempted annotation contributes one entry even when several checks fail.
- `ValidatedDataset`: source path, `input_sha256`, sorted images, contiguous integer-to-name
  `names`, invalid `errors`, and `input_boxes` count (excluding explicit backgrounds).
- `PreparedDataset`: native `data` path, `ground_truth` cleaned CSV path, `manifest` JSON
  path, selected `dataset_format`, and explicit list of non-image `artifacts` paths.

The parser preserves labels as strings (including numeric-looking names), retains class
names found on invalid boxes, and sorts names lexically for deterministic IDs. It rejects
missing columns, image names differing from file basenames, inconsistent identity/path/split
assignments, duplicate background rows or duplicate numeric valid boxes,
and mixed explicit background/annotation records. Geometry failures and missing labels on
attempted boxes are counted and dropped. Fully blank label/coordinates mean background.

Cleaned CSV records use the established eight-column schema and absolute original image
paths. Images with no remaining boxes get one background row. Input is never overwritten.

## State Transitions

Fresh output reservation → full input validation/cleaning → cleaned CSV and preparation
record → selected native dataset export → training → shared cleaned evaluation.

Errors retain owned diagnostics. A failed preparation never returns a ready dataset.
The preparation record retains input fingerprint, original/resolved/generated identity,
class names, split and box counts, dropped rows/reasons, and the selected representation.
Native-setting overrides are recorded separately by training and pipeline integration.
