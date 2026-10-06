# Publisher Contract

`create_publisher(FiftyOneConfig | None)` returns a `Publisher` with `enabled`,
`preflight()`, and `publish(PublicationRequest) -> PublicationReceipt | None`.
The request carries the task ID, effective/source GT paths, optional raw prediction
path and known inference splits, per-split evaluation JSON paths, and metadata.
The owner writes the returned receipt to its output directory and records its meaningful
dataset/run link in the canonical run Configuration Object. The receipt remains local and is
not uploaded as a ClearML artifact. No FiftyOne or ClearML objects cross the publisher interface.

`NoOpPublisher` imports no FiftyOne. The optional publishing adapter/backend/plugin
modules contain FiftyOne imports and record
one sample per image, raw predictions separate from evaluated fields, and
task-ID-namespaced run fields. Native evaluation registration is permitted; it consumes
existing digital-metrics matches and reports without rematching. Backend errors may
propagate to the shared command boundary, which logs a warning and continues the task.
Factory/import or preflight failure selects a no-op publisher for that invocation.
Request construction, publication, local receipt writes, and visualization run-link
recording are optional: their errors cannot fail otherwise successful computation.
Cancellation and process-exit signals retain their normal interruption behavior.

Warnings identify the failed operation (`factory`, `preflight`, `prepare_request`,
`publish`, `write_receipt`, or `record_configuration`), exception type and redacted
message/cause, with available task and path context. DEBUG adds stack locations
without source excerpts or local-variable values. Credential-bearing URLs and
sensitive labeled values are redacted before logging. Loguru's existing DEBUG
default remains; `LOGURU_LEVEL=INFO` selects concise output. Caller-owned sinks
are not replaced. No-receipt results remain a warning without successful publication.

Receipt fields map semantic names (`predictions`, `matched_ground_truth`,
`matched_predictions`, `evaluated_predictions`, `predicted`, `evaluated`, `tp`, `fp`, `fn`) to stored sample
fields. Run namespaces use the full SHA-256 of the task ID; `dataset.info.cy_runs`
retains the original ID, fields, source hash, methodology, thresholds, and completion.
Unknown inference membership is null for an image with no CSV predictions when the
caller cannot supply inference splits; evaluated membership is always explicit.

The receipt also records `dataset_complete`, `run_complete`, resolved `payload_paths`
(`ground_truth`, optional `source_ground_truth`/`predictions`, and `evaluation_<split>`),
an `evaluation_keys` mapping from each evaluated split to its native evaluation key
(default `{}` for legacy receipts and prediction-only imports), and an aware UTC
`published_at` timestamp. The canonical run link includes this mapping. The receipt is
emitted only after saving both completion markers and all task-owned evaluation results.
Effective GT identity hashes the same bytes that are parsed.

Raw prediction boxes preserve finite, ordered coordinates, including zero width or
height produced by native image-boundary clipping. Publication retains these rows,
confidence values, and original CSV indices without filtering or enlarging boxes.
Reversed coordinates, non-finite coordinates, and confidence outside finite `[0, 1]`
are rejected. Labelled ground-truth boxes must have strictly positive width and height.

Malformed JSON, non-mapping JSON and unreadable optional FiftyOne configuration warn and fall
back to filesystem defaults during CLI initialization. Explicit directory environment selections
remain authoritative. Help, config export and computation can proceed; enabled visualization
still uses the optional warning/no-op publisher boundary if the backend rejects its configuration.

## Native evaluations and App extension

The [native evaluation amendment](../../015-fiftyone-native-evaluations/contracts/native-evaluation.md)
defines one persisted detection evaluation per task/split, method `digital_metrics`.
Its view includes the payload images and backgrounds. Source matches determine statuses
and counts; the existing claimed-GT rules determine canonical confusion entries. Raw
predictions remain intact. `matched_predictions` preserves the complete audit overlay,
including `filtered` detections. Native evaluations use `matched_ground_truth` and
`evaluated_predictions`, whose prediction detections exclude `filtered` boxes. This
keeps native evaluation patch views from counting excluded predictions as unmatched
false positives; filtered audit detections have no native evaluated status. Persisted label IDs support exact selection. Saved results
support discovery, reload, reports, confusion matrices, evaluation patches, rename and
delete. Same-task retry repairs its fields and evaluations while preserving other tasks.

`EvaluationPayload` remains schema version 1 and adds an optional versioned report:
ordered classes, exact confusion matrix, existing IoU 0.50 PR curves, and per-class
AP50/AP75/AP50_95. No GT means unavailable AP (null); GT with no predictions means AP
zero. Legacy payloads remain readable without inventing missing report data. Full-split
mAP is mean AP50_95 over classes with GT. mAR and restricted-subset AP/PR are unavailable;
fixed-threshold subset counts restore to the full report when the subset context exits.

The separately installed `@clearml-yolo/evaluation` plugin provides `native_evaluation`
for exact wrong-class counts/navigation and `evaluation_reports` for AP and PR. Install
it in the same server Python environment as the backend and `clearml-yolo`, then restart
App:

```bash
uv run python -c 'from clearml_yolo.publishing.fiftyone_panel import install_evaluation_plugin; print(install_evaluation_plugin())'
```

Publication does not globally install the plugin. Existing runs gain native evaluations
only through new publication/reruns; there is no automatic historical migration.
