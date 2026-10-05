# Tracking and Publication Contract

## Public execution interfaces

All existing commands/options remain unchanged. Each execution invocation owns one ClearML task; pipeline stages reuse it. Native metric names, epoch indices and plotting choices remain authoritative.

## Distributed telemetry

Owner dispatches native completed epoch observations while DDP is running. Events dispatch once in journal order under the owner invocation context. Partial records wait; malformed or incomplete final journals fail. Final on_train_end executes only after full drain and completeness validation. Existing relay context-manager/replay interfaces remain compatible.

## Console publication

The invocation-owned task enables ClearML stdout/stderr stream capture. Normal terminal
output emitted while that task is active, including native YOLO output, is forwarded to the
task Console. Argument-parser and framework auto-capture remain disabled. Nested stages reuse
the owner task, and workers do not create tasks or independently publish console streams.

Configuration Objects and General parameters retain credential sanitization. Console
stdout/stderr is raw and is not passed through that sanitizer, so callers must not print
credentials. This contract does not backfill historical tasks, cover output emitted after
the task closes, or guarantee forwarding from DDP subprocess streams.

## Publication inventory

| Destination | Permitted contents |
|---|---|
| Console | Raw stdout and stderr captured during the invocation-owned task lifetime, including native YOLO output. |
| Scalars / Plots / Debug Samples | Installed native training/validation telemetry and project performance visualization. |
| Output Model | One native best checkpoint, verified before successful completion. |
| Artifacts | Canonical ground truth, prediction, frozen validation-threshold CSVs; evaluation/comparison workbooks; final performance reports. |
| Configuration Objects / General | Sanitized execution settings, dataset overrides, source references, normalization and meaningful provenance. |
| Local outputs | Effective YAML with comments, temporary inputs, manifests, journals and diagnostic/publication receipts. |

No numbered YAML, train_data_overrides.json, configuration copies, replay manifests or diagnostic receipts appear as artifacts. No duplicate checkpoint artifact is uploaded. CSV byte deduplication retains logical publication expectations.

## Recovery and failure

Replay uses the current task's canonical configuration. Task-backed model recovery follows
[the recovery amendment](../../012-remove-legacy-compatibility/contracts/task-recovery.md):
explicit threshold maps are authoritative; ordered threshold payloads then dashboards provide
stored thresholds, with dashboard rounding/calibration-provenance warnings. A present malformed
source fails without fallback. Output models are preferred; ordered checkpoint artifacts apply
only if no output models exist. One checkpoint selection determines both weights and source
task/model links or task/artifact identity; artifacts have no fabricated model link. Recovery
does not fetch historical predictions, Configuration Objects or General parameters over current
comparison settings. Both positions use current images/settings and frozen thresholds; old
architecture loading is not guaranteed. Current native publication stays unchanged.
Existing remote override, resolution, secret redaction and local execution-copy behavior remain intact.

Any computation, callback, journal, upload, flush or interruption error fails command/task and preserves local diagnostics. Prior telemetry on a failed task is valid partial evidence, never a completion signal. Historical tasks are not modified.

Failure finalization closes the invocation-owned SDK handle before marking failure through a
fresh task handle. This prevents the SDK status monitor from treating the application's own
failure transition as an external abort. Finalization errors and local filesystem cleanup errors are logged by type without replacing
the original computation/upload/flush/interruption exception. If SDK closure itself fails, safe
monitor shutdown cannot be established and the failed remote transition is not guaranteed.

Canonical executable configuration preserves explicit empty strings, lists and mappings, including
native `classes=[]`. Empty optional result provenance is still omitted. Redaction affects published
snapshots rather than executable inputs and includes AWS `X-Amz-Signature` and Google
`X-Goog-Signature` mapping/query keys along with existing credential fields.
