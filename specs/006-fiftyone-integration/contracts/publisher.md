# Publisher Contract

`create_publisher(FiftyOneConfig | None)` returns a `Publisher` with `enabled`,
`preflight()`, and `publish(PublicationRequest) -> PublicationReceipt | None`.
The request carries the task ID, effective/source GT paths, optional raw prediction
path and known inference splits, per-split evaluation JSON paths, and metadata.
The owner writes the returned receipt to its output directory and records its meaningful
dataset/run link in the canonical run Configuration Object. The receipt remains local and is
not uploaded as a ClearML artifact. No FiftyOne or ClearML objects cross the publisher interface.

`NoOpPublisher` imports no FiftyOne. `FiftyOnePublisher` is the sole importer and records
one sample per image, raw predictions separate from evaluated fields, and
task-ID-namespaced run fields. It performs no matching/evaluation. Backend errors may
propagate to the shared command boundary, which logs a warning and continues the task.
Factory/import or preflight failure selects a no-op publisher for that invocation.
Request construction, publication, local receipt writes, and visualization run-link
recording are optional: their errors cannot fail otherwise successful computation.
Cancellation and process-exit signals retain their normal interruption behavior.

Receipt fields map semantic names (`predictions`, `matched_ground_truth`,
`matched_predictions`, `predicted`, `evaluated`, `tp`, `fp`, `fn`) to stored sample
fields. Run namespaces use the full SHA-256 of the task ID; `dataset.info.cy_runs`
retains the original ID, fields, source hash, methodology, thresholds, and completion.
Unknown inference membership is null for an image with no CSV predictions when the
caller cannot supply inference splits; evaluated membership is always explicit.

The receipt also records `dataset_complete`, `run_complete`, resolved `payload_paths`
(`ground_truth`, optional `source_ground_truth`/`predictions`, and `evaluation_<split>`),
and an aware UTC `published_at` timestamp. It is emitted only after saving both completion
markers. Effective GT identity hashes the same bytes that are parsed.

Raw prediction boxes preserve finite, ordered coordinates, including zero width or
height produced by native image-boundary clipping. Publication retains these rows,
confidence values, and original CSV indices without filtering or enlarging boxes.
Reversed coordinates, non-finite coordinates, and confidence outside finite `[0, 1]`
are rejected. Labelled ground-truth boxes must have strictly positive width and height.
