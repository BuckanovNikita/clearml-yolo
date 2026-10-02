# Native model metadata mapping

| Field | Authoritative source | Write policy |
|---|---|---|
| Name | native trainer.args.name and best checkpoint role | Update existing native record |
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
| IDs/timestamps | ClearML server | Never write fabricated values |

Do not copy model training parameters into comparison Configuration Objects. Read class names
and design from the downloaded checkpoint. Completed-task recovery requires exactly one current
Output Model marked with the `best` role; absence or ambiguity fails. During native callback
finalization, the local `best.pt` basename identifies the model before that role metadata is
enriched and verified. Checkpoint artifacts are not a recovery source.
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
