# CSV Training CLI and Publication Contract

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
class mapping and original/generated image identity inventory. `dataset.ndjson`,
`preparation.json`, `labels.zip`, generated labels, conversion byproducts and
requested/effective native YAML are local cache or run diagnostics.

The cleaned canonical `ground_truth.csv` is the performance artifact. Generated `data.yaml`
is attached as the consumed `dataset` Configuration Object. Requested/effective dataset-policy
changes are stored in the canonical run Configuration Object under `training_data_overrides`
or `prediction_data_overrides`. Raw source dataset images are never uploaded as artifacts;
owner-only native training/validation previews remain permitted. `TrainResult` adds optional
`cleaned_ground_truth` and `dataset_reference` paths so pipeline consumers receive actual
prepared outputs. Legacy training leaves them null. No stage creates a second tracking task.
