# Native model metadata mapping

| Field | Authoritative source | Write policy |
|---|---|---|
| Name | requested native name, project-local collision resolution and best checkpoint role | Update existing native record; share experiment suffix when needed |
| Task/project | invocation task | Preserve native association |
| Framework | actual PyTorch checkpoint | PyTorch framework |
| Architecture/design | trained model YAML and architecture reference | model design/config text |
| Label enumeration | checkpoint/trained model names | SDK label-to-integer mapping |
| Tags | invocation task tags plus best-checkpoint role | No production tag invented |
| Description | actual training task/checkpoint role | Concise factual description |
| Lineage | known source input model if registered | Preserve known association; otherwise absent |
| Checkpoint role/file/hash | actual best.pt | SDK metadata; role=best |
| Versions | installed ClearML, Ultralytics, Torch and project | SDK metadata |
| Input shape/settings | trainer effective args (imgsz/channels where known) | SDK metadata |
| Requested/effective names | invocation naming state | `clearml_yolo_requested_model_name` / `clearml_yolo_effective_model_name` string metadata |
| Calibrated class thresholds | full-precision validation calibration from prediction checkpoint | Owned best model only, after checkpoint association and remote readback |
| IDs/timestamps | ClearML server | Never write fabricated values |

Do not copy model training parameters into comparison Configuration Objects. Read class names
and design from the downloaded checkpoint. Native completion requires exactly one current
Output Model marked with the `best` role; absence or ambiguity fails. During native callback
finalization, the local `best.pt` basename identifies the model before that role metadata is
enriched and verified. Historical task-backed recovery follows the
[ordered recovery contract](../../012-remove-legacy-compatibility/contracts/task-recovery.md),
including artifact fallback only when the source task has no Output Models. Artifact
fallback does not satisfy a new native invocation's model-completion requirement.
The invocation requires successful native registration and verified remote weights before
completion; missing registration must not create a wrapper fallback model.

## Installed SDK contract

ClearML 2.1.10 native update_output_model starts an asynchronous upload. wait_for_uploads
and task.flush are barriers only: they wait without re-raising asynchronous exceptions.
After the barrier, reload the task, require its unique best output model and correct
original_task/project, reject uploading_file/failed_uploading URLs, force-download through
get_local_copy(extract_archive=False, raise_on_error=True, force_download=True), and compare
its nonempty file SHA-256 with local trainer.best. Enrich using OutputModel(base_model_id=id)
and require unchanged identity immediately (constructor can suppress failures), update public
metadata, then verify fields with a fresh Model(model_id=id). Never call update_weights twice.
Unknown parent lineage stays untouched; only known registered input-model IDs become metadata.

Verification treats tags as an unordered set and compares documented metadata value/type
fields; the SDK may add server bookkeeping keys. Unavailable package versions are omitted.

## Display identity and calibrated thresholds

Follow the [evaluation publication amendment](../../014-evaluation-publication/contracts/publication.md)
for task/model naming. Unused requested names remain unchanged. Exact project-local
collisions include archived records and exclude current task/model IDs. A readable
adjective–noun suffix is shared by the experiment and its owned best model; resolve and
recheck for up to 20 generated suffixes, then fail rather than accepting a collision.
Clones resolve names afresh. Display names do not change output paths, checkpoint URLs,
model IDs, task/project association or model count.

Only an invocation-owned, already verified native best model can receive calibration
metadata. Standalone metrics has no owned model handle and must skip this association;
it neither creates models nor changes another task's model. Calibration requires split
`val`, a valid full-precision threshold map, and the SHA-256 of the checkpoint actually
used for prediction matching the owned best model's downloaded bytes. Missing or
mismatched provenance fails; a caller-claimed path alone does not prove association.

The metadata keys are:

- `clearml_yolo_confidence_thresholds`: exact float JSON, type `str`.
- `clearml_yolo_confidence_threshold/<class_name>`: each `repr(float)` value, type `float`.
- `clearml_yolo_calibration_split`: `val`, type `str`.
- `clearml_yolo_calibration_checkpoint_sha256`: prediction checkpoint hash, type `str`.

Verify the original model before writing and reload after writing. Require unchanged
model ID/task/project/URL and downloaded SHA-256 plus exact metadata value/type readback.
Extend the original completion barrier with threshold expectations; enrichment does not
create another model or upload weights again. These requirements do not replace the
canonical `metrics_best_confidences_val` CSV or historical threshold recovery sources.
