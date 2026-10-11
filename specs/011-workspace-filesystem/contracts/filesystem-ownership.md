# Filesystem ownership contract

The maintained normative contract is [Filesystem ownership](../../../docs/filesystem-policy.md).
This feature contract records the current surface used by implementation and tests.

## Public selection rules

- `CY_HOME` selects the automatic workspace and defaults to the launch working directory.
- Explicit data/output/cache paths retain their values. Library configuration selectors must
  resolve inside the physical project root, including through symlinks; outside selectors fail.
- `dataset_cache_dir=null` always uses the workspace cache and ignores ambient `XDG_CACHE_HOME`;
  an explicit `dataset_cache_dir` remains authoritative.
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
| CSV dataset cache | `$CY_HOME/.cache/clearml-yolo/datasets` |
| Ultralytics downloaded datasets and weights | `$CY_HOME/.cache/ultralytics/datasets`, `$CY_HOME/.cache/ultralytics/weights` |
| Ultralytics settings | `$CY_HOME/.config/Ultralytics` |
| ClearML downloads and cache | `$CY_HOME/.cache/clearml` |
| FiftyOne datasets, dataset zoo and database | `$CY_HOME/.cache/fiftyone` |
| Owned temporary work | `$CY_HOME/.tmp` |

Feature 024 routes exercised XDG and SDK configuration/cache settings into the project.
The stdlib bootstrap runs before SDK imports. Matplotlib/fontconfig, Torch/CUDA/Triton,
Numba/Hugging Face, Python bytecode, ETA, Requests/netrc, AWS and all five FiftyOne
configuration selectors use project-owned paths. `TMPDIR`/`TMP`/`TEMP` and `tempfile`
are scoped to an invocation arena through native work, publication, uploads and task
finalization. Cleanup requires no live owned participant; abandoned recovery requires
identity/liveness and lease evidence. Shared user-wide GPU queue locks/registry stay
outside the arena and are captured before project XDG overrides.

## Source and publication invariants

- Training requires CSV ground truth and prepares its native data reference in the shared dataset
  cache. Source images remain immutable; cache identity and locking follow the CSV dataset contract.
- Sanitized Configuration Objects retain supported source fields.
- Adjacent comparison temporary files exist only for same-filesystem atomic replacement and are
  removed on every exit path.
- Ambient home/system configuration is not read. Explicit project configuration is preserved.
  Explicit FiftyOne data paths remain selected.
  `CLEARML_CACHE_DIR` is the supported explicit ClearML cache setting. `HOME` is unchanged.

## Boundary

The contract governs automatic paths owned by clearml-yolo and the named dependency data stores.
External scripts, plugins and runners remain outside the command boundary. Package defaults
and OS runtime assets remain available. Imports stay inert; programmatic callers explicitly
establish runtime initialization and invocation ownership.
