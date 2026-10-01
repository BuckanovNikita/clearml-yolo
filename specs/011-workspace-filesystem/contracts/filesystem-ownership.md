# Filesystem ownership contract

The maintained normative contract is [Filesystem ownership](../../../docs/filesystem-policy.md).
This feature contract records the compatibility surface used by implementation and tests.

## Public selection rules

- `CY_HOME` selects the automatic workspace and defaults to the launch working directory.
- Explicit command paths and supported dependency environment variables retain their values.
- `dataset_cache_dir=null` uses explicit `XDG_CACHE_HOME` when present, then the workspace cache.
- Existing or explicitly pathed checkpoints remain inputs. An absent bare `.pt` name uses the
  workspace Ultralytics weight cache.
- Pipeline prediction preserves the original reference string. Local comparison requires a
  filesystem checkpoint and reuses the selected native cache for bare checkpoint names.
- A physical-home write destination warns once and remains accepted.

## Automatic locations

| Content | Location |
|---|---|
| Runs and latest shortcut | `$CY_HOME/runs` |
| Hydra outputs and sweeps | `$CY_HOME/outputs`, `$CY_HOME/multirun` |
| CSV dataset cache | `$CY_HOME/.cache/clearml-yolo/datasets` unless XDG is explicit |
| Native YAML dataset copies | `$CY_HOME/.cache/clearml-yolo/native-datasets` |
| Bare checkpoint downloads | `$CY_HOME/.cache/ultralytics/weights` |
| Supported dependency caches | `$CY_HOME/.cache` |
| Supported dependency configuration | `$CY_HOME/.config` |
| Owned temporary work | `$CY_HOME/.tmp` |

## Source and publication invariants

- Native source YAML, images and labels are read-only inputs. Native repairs and generated caches
  operate on owner-writable real staged copies under a lock held through training. Original file
  permissions remain unchanged. Identity includes resolved text-manifest membership, including
  cwd-relative entries; native duplicates and ordering remain intact.
- Moving a resolved native YAML execution copy does not change its relative split membership.
- Sanitized Configuration Objects retain source fields; execution-only path anchoring is local.
- Adjacent comparison temporary files exist only for same-filesystem atomic replacement and are
  removed on every exit path.
- Existing user configuration is read-only. `HOME` is unchanged.

## Boundary

The contract governs automatic paths used by clearml-yolo and its supported dependency setup.
External scripts, plugins, runners and the interpreter's initial package import require their own
workspace/cache controls.
