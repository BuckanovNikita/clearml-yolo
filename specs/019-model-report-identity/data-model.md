# Data model

`ModelIdentity` is frozen: nonempty `model_name`, optional full `training_task_id`,
optional `checkpoint_sha256`, and optional registered `model_id`. A custom label
has no invented task/model ID. Checkpoint metadata is hash-validated on recovery.

Prediction provenance binds prediction and checkpoint bytes to `model_identity`.
Evaluation payloads and result contexts carry that same value. Context CSV columns
flatten the name and source task ID while JSON retains the complete value.

Comparison manifests contain separate `baseline_identity` and `candidate_identity`.
Workbook annotations persist role identities and original layout metadata, allowing
safe reading of both new and historical dashboards.
