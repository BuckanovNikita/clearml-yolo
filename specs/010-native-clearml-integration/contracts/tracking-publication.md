# Tracking and Publication Contract

## Public execution interfaces

All existing commands/options remain unchanged. Each execution invocation owns one ClearML task;
pipeline stages reuse it. Native metric names and epoch indices remain authoritative.
The [readable plot amendment](../../020-readable-evaluation-plots/contracts/plots.md)
excludes native validation PR images from ClearML Plots. The project owner callback adapter
filters `*PR_curve` entries from trainer/validator plot mappings only during the installed
`on_train_end` callback and restores those mappings even on failure. It preserves other
native figures, image previews, scalars, best-model uploads and callback state; DDP owner
replay uses the same adapter. Upstream callback functions and local native plot files remain intact.

## Script and Git metadata

New local execution tasks record their canonical Python module as `script.entry_point`
(`-m clearml_yolo.entrypoints.<stage>`) and repository-root `script.working_dir` (`.`).
When the imported application comes from a source checkout, its Git `origin` URL,
current branch and exact HEAD commit populate `repository`, `branch` and `version_num`.
Discovery uses the imported source location, including linked worktrees, independently
of the launch directory or virtual-environment console wrapper. Detached checkouts
record `HEAD` as the branch selector and retain the exact commit.

Publication occurs once inside the owner lifetime before the workflow starts, with
SDK readback checking the written fields. Rejected metadata fails the task. Nested
stages reuse these fields; ClearML Agent replay preserves its supplied script metadata.
The script record excludes raw command arguments and uncommitted code diffs; URL
credentials are removed/redacted. A recorded commit identifies the checkout's base
revision, not any uncommitted edits. Configuration publication keeps its existing
sanitization and replay behavior.

Without a source checkout, Git or an origin remote, unavailable Git fields remain
unavailable with a warning; module and working-directory publication still works.
An installed wheel never adopts the identity of an unrelated enclosing checkout.
Historical tasks are not backfilled.

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

## Stable parameters and full replay

The [stable parameter amendment](../../036-stable-clearml-cache/contracts/cache.md)
owns the exact publication and cache policy. Native `General` excludes `device`,
`project`, `name`, `save_dir`, `exist_ok` and CSV-owned generated `data`; remaining
scientific arguments and nested semantic names/paths remain intact. Native owner
callbacks, DDP owner replay and other detector publication use the same projection.
This filters new connection inputs; it does not delete General keys inherited by
clones of historical templates. Canonical replay and cache normalization still
handle those keys without cleaning parameter history.

The shared CLI's canonical `run` retains full sanitized native input groups, including
`ultralytics`; embedding callers own complete input recording within their invocation.
New snapshots are JSON; historical HOCON remains readable for replay. Remote YOLO training
restores full native settings and applies scientific `General` overrides while
retaining current output routing. Omitted devices are restored from `run` with their
original values. Filtering never changes native arguments or credential redaction.

External controllers opt into `normalize_task_hash` before cached jobs are created;
publication inside the worker cannot change an earlier cache lookup. The helper
normalizes only recognized clearml-yolo tasks and known execution-only fields,
preserving scientific inputs, unknown fields and code/container identity. GPU indices
are equivalent only at equal CUDA device count. Generated dataset paths require
recorded cache identity/root; unproven paths and unsupported configuration text remain
hash-sensitive. See the [controller recipe](../../../TECH_DETAILS.md#clearml-pipeline-cache-identity).
A cache hit reuses existing remote outputs without writing a new local destination.

## Accurate startup configuration

The CLI publishes `run` as detached, resolved JSON after YAML/CLI composition, queue device
binding and supported remote overrides. It contains selected executable inputs: YOLO retains
its active native groups with only model backend/preset selectors; alternative detectors
retain `model` settings and omit inactive YOLO groups. Later result provenance cannot replace
these configured roots. Native normalization is recorded separately under its existing
normalization/evidence fields. Historical replay remains supported and old tasks are untouched.

A second JSON Configuration Object, `run_overrides`, contains only recursive differences
from built-in project defaults for the same command and selected model preset. It includes
YAML and CLI changes, preserves meaningful false/zero/null/empty values and list order,
and prunes unchanged values and empty parents produced by pruning. Generated routing,
tracking destinations/tags, result provenance and inactive groups are excluded. Both objects
are sanitized; `run_overrides` is deterministic and informational. Cloning and execution
continue to use `run`, and the recognized-task cache projection ignores `run_overrides`.

Training publishes sanitized, validated `General` parameters before dataset preparation,
after remote overrides have been applied. Native callbacks refresh observed normalization
through their existing owner-only lifecycle, including DDP and alternative detectors.
The existing parameter exclusions remain. Commands that skip training do not create training
parameters. Embedded workflows use the tracking port for early General and must still supply
their own complete executable run mapping.

Complete artifacts follow the [publication timing contract](../../014-evaluation-publication/contracts/publication.md#invocation-csv-bundle).
Finalization remains a verification barrier: an earlier complete upload survives later failure,
but upload rejection or a failed final flush fails the task.

## Publication inventory

| Destination | Permitted contents |
|---|---|
| Console | Raw stdout and stderr captured during the invocation-owned task lifetime, including native YOLO output. |
| Scalars / Plots / Debug Samples | Native non-PR training/validation telemetry; current-model confusion charts and test-only grouped PR; training/validation previews. Comparison headline single values remain outside Plots. |
| Output Model | One native best checkpoint, verified before successful completion. |
| Artifacts | Canonical ground truth, prediction, frozen validation-threshold CSVs; evaluation/comparison workbooks; final performance reports. |
| Configuration Objects | Full sanitized `run`, informational `run_overrides`, consumed configuration, source references, normalization and meaningful provenance. |
| General | Sanitized native experiment settings with known execution-only parameters excluded. |
| Execution / Script | Source repository, branch, commit, canonical module entrypoint and repository-relative working directory; no raw arguments or code diffs. |
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
architecture loading is not guaranteed. Native publication follows the PR exclusion above.
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
