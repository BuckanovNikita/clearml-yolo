# Frozen integration interfaces

`result_schema.py` owns neutral Pydantic payloads:

- `ResultContext(context_id: str, model_id: str, split: str)`.
- `ConfusionMatrixPayload(labels: list[str], counts: list[list[int]])`.
- `PRCurve(class_name: str, recall: list[float], precision: list[float],
  confidence: list[float], tp: list[int], fp: list[int], gt_count: int,
  ap50: float | None, integration_method: str)`; points have equal lengths.

`clearml_report.py` adds `report_confusion_matrices(task, context, matrix)` and
`report_pr_curves(task, context, curves)`. Use raw Plotly-compatible dictionaries with
SDK `report_plotly`; no new plotting dependency. task=None is a no-op.

`scoring.EvaluatedSplit` gains `confusion_matrix`, `pr_curves` and `result_rows`.
`result_rows` is a context-neutral combined frame for its split with original fields,
row_type, source_row_id/object_id, evaluation_status/exclusion_reason,
confidence_threshold/is_below_threshold and JSON match relationships. Parent adds
context/model identity during persistence. Scoring accepts optional keyword
`source_ground_truth` and `source_predictions` for complete unfiltered export.
Source IDs are assigned BEFORE preprocessing; reserved `source_row_id` persists through
reset_index and upstream preprocessing. Explicit prepared-index-to-source mapping is
required, never coordinate-based joining. `assign_source_ids(frame, row_type=...)`
preserves explicit unique IDs or assigns position-based IDs before transformation;
`build_ground_truth_rows`, `build_prediction_rows` and `build_result_rows` construct
the neutral export frames.

`clearml_session` adds owner-only pre-finalization callbacks and invocation resources.
`clearml_results` owns a durable local shard directory, registration of effective GT,
prediction contexts keyed by source path/role/split, enrichment on evaluation, deterministic
final assembly and once-only `gt_csv`/`predicts_csv` uploads. Completion expectations are
registered before publication; callbacks execute before artifact/model barriers and flush.

`clearml_naming` owns naming state and public collision resolution using SDK queries,
including archived project-local tasks/models and excluding current IDs.
`initialize_naming(task)` stores invocation state; `resolve_model_name(task,
requested_name, model_id=..., write_model_name=...)` runs the actual model writer
inside the bounded retry loop before rechecking both names.
`clearml_native` retains finalize_native_model return compatibility, offers owned-model
registration/threshold association hooks, and keeps completion verification coherent
after enrichment. `owned_native_model(task)` retrieves the registered handle;
`associate_calibration_thresholds` verifies checkpoint association and metadata readback.
Calibration provenance
must identify the checkpoint hash used by prediction, not merely a caller-claimed path.

## Canonical remote command outputs

- ground-truth/train: effective GT; train also native model and existing telemetry.
- predict: effective GT and combined not-evaluated prediction context.
- metrics/val: GT, combined contexts, metrics_best_confidences_val, full/DTRK per
  evaluated split and interactive plots.
- compare: GT, separate reinference contexts, full/DTRK and interactive plots per
  model/split; comparison workbook plus exclusions when paired, candidate-only outputs
  and recorded skip reason when automatic baseline is absent.
- report: existing developer/business report workbooks only.
- pipeline: union of enabled stages, CSVs once; test comparison/report workbooks unchanged.

Keep local diagnostics, configuration/provenance, comparison plots and optional FiftyOne
receipt/link. Stop publishing duplicate evaluation summary workbooks, separate matches,
per-split threshold/methodology sidecars and raw prediction artifacts.
