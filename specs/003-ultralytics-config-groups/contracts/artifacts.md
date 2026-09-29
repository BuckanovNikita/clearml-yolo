# Native configuration artifact contract

Training writes `ultralytics.yaml`; prediction writes `ultralytics_predict.yaml` in the
applicable stage output directory. Distinct splits and comparison roles also receive effective
native YAML with actual checkpoint, source manifest, mode and output routing. Prediction source
manifests remain local after execution so the native YAML can be replayed against original inputs.

Active YAML values match native execution; irrelevant parameters are commented. Original upstream
comments, license header and order remain. Files contain no Hydra wrapper keys or unresolved
interpolation and are accepted directly by native Ultralytics configuration loading.

Native YAML stays local with comments and replay manifests. Canonical sanitized run
configuration and native General training parameters support remote clones. Only consumed
dataset/explicit report Configuration Objects are separate; no downloadable configuration copies.
Credentials stay excluded; native owner-only training and validation previews are permitted.

Required artifacts and the single native best model must be verified and flushed before
completion. See the current [publication inventory](../../008-dataset-clearml-tracking/contracts/publication.md).
