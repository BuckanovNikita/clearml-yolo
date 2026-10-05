# Current data contracts

- `TrainResult` contains weights, save directory, effective arguments, cleaned ground truth
  and prepared dataset reference. Prepared paths are required after successful CSV training.
- A recoverable ClearML task exposes a best Output Model and `metrics_best_confidences_val`
  CSV with exactly `class_name,confidence`, unique nonempty names and finite values in [0, 1].
- Comparison has one `EvaluationConfig`; scoring split does not select a threshold source.
- Prediction settings consume only the resolved prediction group and explicit weights.

## Approved recovery data amendment (2026-10-05)

The current-only recoverability bullet above is superseded by
[task recovery](contracts/task-recovery.md). A recovered source contains the source task ID,
a selected output-model identity/link or selected artifact name, and one validated local
`.pt` path. Artifact sources have no model identity/link. This same selection feeds weights
and comparison provenance. A frozen threshold map has nonempty unique string class names
and finite values in [0, 1]; dashboard-derived maps additionally disclose rounding and
unavailable calibration provenance. The current comparison settings/images remain separate
from all source-task historical predictions and configurations.
