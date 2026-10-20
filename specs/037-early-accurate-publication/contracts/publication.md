# Configuration and publication interface decisions

Hydra composes built-in defaults for the selected command/preset without the user's YAML
or CLI values. It removes inactive backend groups from detached executable mappings.
ClearML publishes run and run_overrides as JSON; differences prune unchanged nested values
but preserve explicit false/zero/null/empty/list-order changes. Execution only replays run.
Native observed parameters remain separate from executable run values.

TrackingSession gains publish_training_parameters(task, values),
declare_result_producers(task, producers, *, output_dir), and
complete_result_producer(task, producer). Producers use Literal names predict, metrics,
compare. The pipeline declares the full enabled set before any result writes; standalone
commands declare their single producer if no pipeline declaration exists. Repeated identical
or subset declarations are allowed while active; unknown/duplicate completion and row writes
after aggregate publication fail. Finalization verifies completion rather than publishing
incomplete aggregates. An empty producer set requires no prediction artifact.

register_ground_truth validates/writes/uploads the canonical effective truth immediately;
identical repeat registration is a no-op, conflicting truth fails. Evaluation publishes after
workbook annotation and before the next model/split or statistics. Complete predictions upload
at last contributor completion, including explicit skipped comparison, before optional work.

DetectorExporter.execute(request, destination, *, artifact_ready=None) accepts an optional
typed Callable[[str, Path], None]. Export producers announce only finalized immutable files;
callbacks propagate failure. The application uploads announced files immediately and verifies
returned artifact inventory without duplicate uploads. Export adapters never import ClearML.

Best model retains native ownership, finalized checkpoint selection and the existing model
barrier. Completed uploads survive later failure; final flush/upload failures fail the task.
