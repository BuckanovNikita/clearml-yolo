# Tracking and Publication Contract

## Public execution interfaces

All existing commands/options remain unchanged. Each execution invocation owns one ClearML task; pipeline stages reuse it. Native metric names, epoch indices and plotting choices remain authoritative.

## Distributed telemetry

Owner dispatches native completed epoch observations while DDP is running. Events dispatch once in journal order under the owner invocation context. Partial records wait; malformed or incomplete final journals fail. Final on_train_end executes only after full drain and completeness validation. Existing relay context-manager/replay interfaces remain compatible.

## Publication inventory

| Destination | Permitted contents |
|---|---|
| Scalars / Plots / Debug Samples | Installed native training/validation telemetry and project performance visualization. |
| Output Model | One native best checkpoint, verified before successful completion. |
| Artifacts | Canonical ground truth, prediction, frozen validation-threshold CSVs; evaluation/comparison workbooks; final performance reports. |
| Configuration Objects / General | Sanitized execution settings, dataset overrides, source references, normalization and meaningful provenance. |
| Local outputs | Effective YAML with comments, temporary inputs, manifests, journals and diagnostic/publication receipts. |

No numbered YAML, train_data_overrides.json, configuration copies, replay manifests or diagnostic receipts appear as artifacts. No duplicate checkpoint artifact is uploaded. CSV byte deduplication retains logical publication expectations.

## Recovery and failure

Replay uses the current task's canonical configuration; model provenance uses its source task's configuration/General without replacing current comparison settings. Exact thresholds come from validation CSVs, with existing historical threshold readers retained. Missing required configuration fails actionably. Existing remote override, resolution, secret redaction and local execution-copy behavior remain intact.

Any computation, callback, journal, upload, flush or interruption error fails command/task and preserves local diagnostics. Prior telemetry on a failed task is valid partial evidence, never a completion signal. Historical tasks are not modified.
