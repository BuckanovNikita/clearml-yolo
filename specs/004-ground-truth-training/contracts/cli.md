# CSV Training CLI and Artifact Contract

`cy ground_truth=truth.csv` trains from the supplied CSV. `cy-train ground_truth=truth.csv`
uses the same conversion. Both accept `dataset_format=ndjson` (default) or `flat`.
Standalone `cy-train` without ground truth retains explicit `ultralytics.data` behavior.
The format is a wrapper parameter, never a native Ultralytics key. No new command.

CSV image paths resolve relative to the CSV directory. Train and val must be nonempty;
the pipeline also requires splits consumed by enabled prediction/metrics/comparison.
Invalid boxes are dropped; the command displays `Invalid bounding boxes dropped: N`
before training. Blank background records do not increment N. No valid training boxes
remaining is fatal after the count is shown. Cleaned ground truth is used downstream.

CSV data overrides native data/filter/class-remapping settings with a visible record.
`resume` is rejected in CSV mode. Unsupported task types are rejected. Dataset configuration
attached to ClearML cannot override the generated data. Device, epochs, batch, AMP,
compilation, and augmentation retain existing precedence.

Preparation writes a cleaned CSV, JSON preparation record, selected native dataset,
class mapping and original/generated image identity inventory. Flat labels and dataset
metadata are retained; images remain local. The invocation records these non-image files
as required artifacts and records effective native YAML with existing comment preservation.
NDJSON is a dataset artifact, not a YAML configuration passed through the YAML-only adapter.

Preparation uses `ground_truth.csv`, `preparation.json`, `data.yaml`, optional
`dataset.ndjson`, and an explicit non-image labels archive. Artifact names are
`dataset_ground_truth`, `dataset_preparation`, `dataset_configuration`, `dataset_ndjson`,
`dataset_labels`, and `train_data_overrides`, as applicable. `TrainResult` adds optional `cleaned_ground_truth` and `dataset_reference`
paths so pipeline consumers receive the actual prepared outputs. Legacy training leaves
them null. No stage creates a second tracking task.
