# Filesystem ownership

All nine commands initialize application-owned filesystem defaults before importing execution
dependencies.
`CY_HOME` defaults to the launch working directory. An absolute value selects another
workspace; a relative value is resolved against the launch directory once. Changing the
process working directory later does not change the captured root. Explicit relative
input and output paths retain their existing working-directory semantics.

## Defaults and explicit destinations

| Content | Default beneath `CY_HOME` |
|---|---|
| Task-owned runs and latest shortcut | `runs/` |
| Hydra logs and sweeps | `outputs/`, `multirun/` |
| Shared CSV datasets | `.cache/clearml-yolo/datasets/` |
| Ultralytics downloaded datasets and weights | `.cache/ultralytics/datasets/`, `.cache/ultralytics/weights/` |
| Ultralytics settings | `.config/Ultralytics/` |
| ClearML downloads and cache | `.cache/clearml/` |
| FiftyOne datasets, dataset zoo and database | `.cache/fiftyone/` |
| Owned execution copies, inference manifests and DDP relay/runtime files | `.tmp/` |

`dataset_cache_dir=null` always selects
`CY_HOME/.cache/clearml-yolo/datasets`, independent of `XDG_CACHE_HOME`; an explicit
`dataset_cache_dir` remains authoritative. Explicit command paths, supported dependency
environment settings and configured native directory values remain valid anywhere. This includes
existing FiftyOne configuration selections for its dataset, dataset-zoo and database directories.
`CLEARML_CACHE_DIR` is the supported explicit ClearML cache setting. Existing ClearML and
FiftyOne configuration can be read from home;
it is neither copied nor rewritten. `HOME` is never reassigned.

The application does not supply workspace defaults for general-purpose dependency or process
state: `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`, Python bytecode, Torch, CUDA, Triton, Numba,
Hugging Face and Matplotlib caches/configuration, ETA state, FiftyOne model-zoo/plugins/config
paths, and `TMPDIR`/`TMP`/`TEMP` plus `tempfile` defaults keep their ordinary environment or
library behavior. Caller-provided values for those settings remain untouched. Application-owned
temporary resources still select `CY_HOME/.tmp` directly.

Write destinations resolving physically beneath the home directory produce a warning,
once per resolved destination in a process. Warnings do not reject, relocate or override
the requested path. Existing symlinks determine the physical destination: a link beneath
home pointing outside it does not make the external target home-resident.

## Inputs and temporary ownership

Training prepares its native inputs from `ground_truth` in the shared CSV-addressed dataset
cache. Source images are immutable; callers invalidate an unused prepared entry after source
corrections. Native defaults for downloaded datasets, weights and runs use the workspace;
explicit configured values remain selected, including NDJSON/platform conversion directories.
Existing local checkpoints remain input files at their original paths. Pipeline prediction
retains remote URI strings and explicit relative references. Local comparison requires a
filesystem checkpoint; resolve remote weights before comparing. Comparison reuses the selected
native cache for bare checkpoint names.

Resolved execution configurations live in owned temporary storage. Untransformed configurations
retain their original input path. Invocation cleanup removes
owned temporary copies on success, failure or interruption. Native workers inherit the
root and scoped settings, and their DDP launcher files are inside the owned runtime directory.

Atomic comparison cache publication uses temporary files beside the selected output so
rename remains atomic when the output is on another filesystem. These files are removed
on serialization, replacement or interruption errors as well as success. Other application-owned
temporary storage uses `.tmp/` without changing process-wide temporary directory settings.

## Launch boundary

This policy routes application-owned writes and the named dependency storage needed for native
execution and publication; it is not an operating-system sandbox for arbitrary user-supplied
scripts or plugins. Python bytecode, external runners such as uv, pytest and pre-commit, and other
general dependency caches/configuration use their standard settings. A caller that needs broader
isolation must configure those tools in its launcher.

Existing caches are not migrated or deleted. Changing `CY_HOME` changes automatic paths;
explicit paths and read-only inputs remain independent of it.
