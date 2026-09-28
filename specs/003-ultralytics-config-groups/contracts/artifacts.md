# Native configuration artifact contract

Training writes `ultralytics.yaml`; prediction writes `ultralytics_predict.yaml` in the
applicable stage output directory. Distinct splits and comparison roles also receive effective
native YAML with actual checkpoint, source manifest, mode and output routing. Prediction source
manifests remain local after execution so the native YAML can be replayed against original inputs.

Active YAML values match native execution; irrelevant parameters are commented. Original upstream
comments, license header and order remain. Files contain no Hydra wrapper keys or unresolved
interpolation and are accepted directly by native Ultralytics configuration loading.

Connect corresponding sanitized YAML as ClearML configuration objects and upload downloadable
YAML artifacts. Stage/split/role identities avoid collisions in the invocation's single task.
Sanitization preserves original comments while removing secrets, including credential-bearing
URLs; dataset images are never uploaded. Local native inputs remain authoritative for replay.

Required writes, uploads and SDK flush precede completion. Failure retains local output and
fails both task and command. Existing checkpoint/metrics/report artifacts remain required.
