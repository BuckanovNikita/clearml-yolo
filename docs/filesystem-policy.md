# Filesystem ownership

All nine commands initialize filesystem defaults before importing execution dependencies.
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
| Writable native YAML dataset copies | `.cache/clearml-yolo/native-datasets/` |
| Bare checkpoint downloads | `.cache/ultralytics/weights/` |
| Dependency caches and Python bytecode after bootstrap | `.cache/` |
| Dependency configuration defaults | `.config/` |
| Owned execution copies, inference manifests and DDP relay/runtime files | `.tmp/` |

Explicit command paths, dependency environment settings and configured native directory
values remain valid anywhere. An explicit `XDG_CACHE_HOME` still controls the default CSV
cache parent. Existing ClearML and FiftyOne configuration can be read from home; it is
neither copied nor rewritten. Existing FiftyOne configuration supplies its explicit
directory selections. `HOME` is never reassigned.

Write destinations resolving physically beneath the home directory produce a warning,
once per resolved destination in a process. Warnings do not reject, relocate or override
the requested path. Existing symlinks determine the physical destination: a link beneath
home pointing outside it does not make the external target home-resident.

## Native inputs and temporary ownership

Native YAML training stages real copies of source images and matching labels in the
shared native cache. Copies are owner-writable even when sources are read-only;
source permissions remain unchanged. Native JPEG repair and label/image cache generation operate on
those copies. Cache entries are locked throughout training, so native writes cannot race
another invocation using the same entry. Staging preserves native sorted image membership,
including repeated entries and manifest paths: `./` entries use the manifest parent;
other relative entries use the process working directory. Cache identity includes resolved
text-manifest membership, so different working-directory targets use different entries.
Source images are assumed immutable; invalidate the unused entry explicitly after source
corrections. Native defaults for downloaded datasets, weights and runs use the workspace;
explicit configured values are retained, including NDJSON/platform conversion directories.
Existing local checkpoints remain input files at their original paths.
Pipeline prediction retains remote URI strings and explicit relative references. Local
comparison requires a filesystem checkpoint; resolve remote weights before comparing.
Comparison reuses the selected native cache for bare checkpoint names.

Resolved execution configurations live in owned temporary storage. A native dataset YAML
without an explicit root receives its original YAML parent as the execution root, keeping
relative split paths valid; the sanitized published configuration retains original fields.
Untransformed configurations retain their original input path. Invocation cleanup removes
owned temporary copies on success, failure or interruption. Native workers inherit the
root and scoped settings, and their DDP launcher files are inside the owned runtime directory.

Atomic comparison cache publication uses temporary files beside the selected output so
rename remains atomic when the output is on another filesystem. These files are removed
on serialization, replacement or interruption errors as well as success. Other temporary
storage uses `.tmp/`.

## Launch boundary

This policy routes application and supported dependency writes; it is not an operating
system sandbox for arbitrary user-supplied scripts or plugins. Python loads the initial
package bootstrap before application code can redirect bytecode. For a cold launch from
outside the installation directory, set `PYTHONPYCACHEPREFIX` beneath the chosen workspace
(or `PYTHONDONTWRITEBYTECODE=1`) in the launcher to cover that initial interpreter write
as well. Subsequent imports use the workspace cache automatically. External runners such
as uv, pytest and pre-commit also require their own workspace cache/temp settings.

Existing caches are not migrated or deleted. Changing `CY_HOME` changes automatic paths;
explicit paths and read-only inputs remain independent of it.
