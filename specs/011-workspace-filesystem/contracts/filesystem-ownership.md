# Filesystem ownership contract

The maintained normative contract is [Filesystem ownership](../../../docs/filesystem-policy.md).
This feature contract records the current surface used by implementation and tests.

## Public selection rules

- `CY_HOME` selects the project workspace and defaults to the launch working directory.
- Explicit inputs, outputs, project cache/temp paths and SDK selectors may resolve outside
  the workspace, including through symlinks. SDK selectors retain their exact values and
  their library's interpretation.
- `dataset_cache_dir=null` uses the workspace cache independently of `XDG_CACHE_HOME`;
  an explicit `dataset_cache_dir` remains authoritative.
- Unresolved checkpoint names, remote URIs and `Path` inputs pass through unchanged.
  Existing local checkpoint strings become `Path` inputs without relocation. Libraries
  choose download/cache locations; local comparison requires a filesystem checkpoint.
- A physical-home write destination warns once and remains accepted.

## Automatic project locations

| Content | Location |
|---|---|
| Runs and latest shortcut | `$CY_HOME/runs` |
| Hydra outputs and sweeps | `$CY_HOME/outputs`, `$CY_HOME/multirun` |
| CSV dataset cache | `$CY_HOME/.cache/clearml-yolo/datasets` |
| Invocation scratch | `${CY_RUNTIME_TEMP_ROOT:-$CY_HOME/.tmp}/cy-runtime-*` |

Bootstrap initializes project paths only. Libraries retain normal configuration/cache
and credential discovery. `HOME`, XDG and all SDK selectors, bytecode settings,
`TMPDIR`/`TMP`/`TEMP` and global `tempfile` defaults remain unchanged. Project temporary
callsites pass their selected directory explicitly. Shared user-wide GPU coordination
stays outside scratch and preserves existing `CY_GPU_QUEUE_ROOT` selections.

Invocations retain their arenas on every exit outcome. Nested scopes reuse scratch;
spawned runtime scopes create separate arenas. No startup scan, abandoned recovery,
ownership heuristic or recursive arena cleanup is permitted. Maintenance is deliberate
and requires an idle workspace and its descendants. Earlier project-local SDK files
are neither migrated nor deleted; reuse requires explicit library configuration.

## Source and publication invariants

- Training requires CSV ground truth and prepares native inputs in the shared dataset cache.
  Source images remain immutable; cache identity and locking follow the CSV dataset contract.
- Native dataset locks fail clearly without soft-lock fallback. Invalid existing entries are
  preserved and reported; repair/removal requires deliberate idle-cache maintenance.
- Sanitized Configuration Objects retain supported source fields.
- Adjacent comparison temporary files exist only for atomic replacement and are removed by
  their writer on every exit path. This permits no generic arena sweeping.
- SDKs discover normal home/system/user configuration. The application supplies no fallback
  config files or private SDK constants. Optional FiftyOne failures retain its warning/no-op
  boundary without changing required ClearML completion.
- Native ClearML callback switches change in memory only and restore on scope exit. Fresh
  DDP trainer construction/training scopes suppress worker ownership without settings-file writes.

## Boundary

The contract governs paths explicitly owned by clearml-yolo. Library stores, scripts,
plugins and runners retain their normal policies. Imports stay inert; programmatic callers
explicitly establish project runtime initialization and invocation ownership.
