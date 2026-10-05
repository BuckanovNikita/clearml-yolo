# Current-only interfaces

- `cy-train` requires `ground_truth`; native `data` is owned by CSV preparation.
- `train()` requires ground truth and returns non-null prepared dataset paths.
- `fetch_best_confidences(task_id)` reads the validation CSV only.
- `resolve_task_weights(task_id)` downloads the current best Output Model only.
- `compare()` accepts `evaluation`, with shared defaults, without top-level matching fields.
- `prediction_settings(ultralytics_predict, weights=None)` has no ignored shared-group input.
- Unsupported wrapper/native/inference keys fail ordinary strict validation, including `+`
  overrides. Non-null native `cfg` remains unsupported.
- `CLEARML_CACHE_DIR` remains canonical; the application does not map `TRAINS_CACHE_DIR`.
- Current explicit run destinations, local checkpoints and exact supplied thresholds remain.

## Recovery-only amendment (2026-10-05)

The threshold-validation-CSV-only and current-best-Output-Model-only bullets above are
superseded by [task-backed model recovery](task-recovery.md). They record the original cleanup
intent. All other interface restrictions remain current; publication itself is unchanged.
