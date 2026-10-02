# Filesystem ownership contract

The maintained normative contract is [Filesystem ownership](../../../docs/filesystem-policy.md).
This feature contract records the current surface used by implementation and tests.

## Public selection rules

- `CY_HOME` selects the automatic workspace and defaults to the launch working directory.
- Explicit command paths and supported dependency environment variables retain their values.
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

General XDG, Python bytecode, Torch/CUDA/Triton/Numba/Hugging Face/Matplotlib, ETA,
FiftyOne model-zoo/plugins/config and generic process/tempfile defaults keep their ordinary
environment or library behavior. Application-owned temporary helpers select `.tmp` directly.

## Source and publication invariants

- Training requires CSV ground truth and prepares its native data reference in the shared dataset
  cache. Source images remain immutable; cache identity and locking follow the CSV dataset contract.
- Sanitized Configuration Objects retain supported source fields.
- Adjacent comparison temporary files exist only for same-filesystem atomic replacement and are
  removed on every exit path.
- Existing user configuration is read-only. Explicit FiftyOne data paths remain selected.
  `CLEARML_CACHE_DIR` is the supported explicit ClearML cache setting. `HOME` is unchanged.

## Boundary

The contract governs automatic paths owned by clearml-yolo and the named dependency data stores.
External scripts, plugins, runners and the interpreter retain their general defaults. Callers
may configure them explicitly when broader isolation is required.
