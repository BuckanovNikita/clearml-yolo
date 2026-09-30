# Native configuration record contract

Training writes `ultralytics.yaml`; prediction writes `ultralytics_predict.yaml` in the
applicable stage output directory. Distinct splits and comparison roles also receive effective
native YAML with actual checkpoint, source manifest, mode and output routing. Prediction source
manifests remain local after execution for native YAML replay against original inputs.

Active YAML values match native execution; irrelevant parameters are commented. Original upstream
comments, license header and order remain. Files contain no Hydra wrapper keys or unresolved
interpolation and are accepted directly by native Ultralytics configuration loading.

Native YAML stays local with comments and replay manifests; it is not a ClearML artifact or
Configuration Object. Canonical sanitized run configuration and native General training
parameters support remote clones. Only consumed dataset and explicit report files are separate
Configuration Objects. Credentials stay excluded; native owner-only training and validation
previews are permitted.

Required artifacts and the single native best model must be verified and flushed before
completion. See the current [publication inventory](../../008-dataset-clearml-tracking/contracts/publication.md).
