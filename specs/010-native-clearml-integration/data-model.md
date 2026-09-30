# Data Model: Native ClearML tracking

## Invocation owner

Existing task ID, owner process ID and ContextVar invocation state. The consumer receives a copy of the current context. Workers are never owners and cannot dispatch native callbacks.

## Journal event

Existing JSONL record schema: callback event plus captured arguments, epoch metrics, losses, model information, validation state and checkpoint paths appropriate to that callback. No public wire-schema change. Complete records are ordered and consumed once; trailing incomplete bytes remain buffered. Unsupported/malformed records are errors.

## Relay lifecycle

States: registered → consuming → stopped/drained → validated → final callback dispatched → parent state applied → finalized/cleaned. Failure from any state stops/joins the consumer and propagates before successful completion. Native on_train_end is retained pending validation. No record dispatch after failure and no double dispatch at final replay.

## Output Model

Existing native model ID, task/project association, uploaded URI and local best checkpoint hash. Finalization requires completed upload, verified flush and forced-download byte equality. Enrichment updates the same model ID.

## Replay configuration and performance evidence

Canonical Configuration Objects and native General hold sanitized execution settings, dataset overrides, normalization and source-task references. Performance artifacts are canonical truth/prediction tables, exact frozen validation thresholds and result/report workbooks. Identical table hashes share one remote artifact. Local diagnostic/manifests/receipts are not artifacts. Compared models resolve source-task configuration without mutating current comparison configuration.
