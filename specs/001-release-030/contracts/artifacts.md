# Tracking and artifact contract

One task owner per invocation; nested stages reuse it, workers never create tasks or publish.
Lifecycle: created -> running -> required artifacts/native model verified and flushed -> completed.
Computation, registration, rejected upload, missing output, flush or interruption errors fail
both task and command and retain local outputs. Credentials must never be captured.

Native callbacks own training Scalars, Plots, Debug Samples and one best.pt Output Model.
Enrich that same model with checkpoint-backed metadata; verify its remote contents before
completion. No wrapper checkpoint/plot copies. Native previews are explicitly permitted.

Artifacts: canonical truth/prediction CSVs, one full-precision validation threshold CSV per
calibrated model, one consolidated evaluation XLSX per split, one comparison XLSX per split,
and final developer/business report XLSX files. Identical CSV bytes are deduplicated.
Valid empty prediction tables remain results. Comparison XLSX includes paired counts,
exclusions, methodology and source task/model links. No duplicate report input workbooks.

Raw metrics, matching JSON, NDJSON, archives, manifests and publication receipts remain local.
Internal required-publication verification remains mandatory without remote bookkeeping files.
One nonempty sanitized run Configuration Object owns wrapper/shared inference/evaluation
settings and meaningful differences/source links. General owns native training arguments.
Only consumed dataset and explicit report configurations remain separately. Local native YAML
retains comments and exact replay manifests; configuration artifacts are not published.

See the complete [before/after inventory](../../008-dataset-clearml-tracking/contracts/publication.md)
and [native model mapping](../../008-dataset-clearml-tracking/contracts/model-metadata.md).
Historical tasks and their readers remain compatible.
