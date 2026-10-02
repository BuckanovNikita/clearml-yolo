# Current data contracts

- `TrainResult` contains weights, save directory, effective arguments, cleaned ground truth
  and prepared dataset reference. Prepared paths are required after successful CSV training.
- A recoverable ClearML task exposes a best Output Model and `metrics_best_confidences_val`
  CSV with exactly `class_name,confidence`, unique nonempty names and finite values in [0, 1].
- Comparison has one `EvaluationConfig`; scoring split does not select a threshold source.
- Prediction settings consume only the resolved prediction group and explicit weights.
