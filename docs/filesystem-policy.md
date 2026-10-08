# Filesystem ownership

The execution commands and `cy-init-config` initialize application-owned filesystem defaults
before importing execution dependencies. `cy-dedup` only resolves its selected cache root;
it does not initialize application directories or dependency settings.
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

The GPU queue is application-owned state but intentionally lives outside `CY_HOME` so commands
from different workspaces coordinate. On Unix-like systems its root is
`$XDG_STATE_HOME/clearml-yolo/queue`, falling back to
`~/.local/state/clearml-yolo/queue`; on Windows it is
`%LOCALAPPDATA%\clearml-yolo\queue`. There is no public queue-root option. Tests may inject an
isolated internal root. The registry, transaction lock, and supervisor/child native liveness locks
belong to this state root. Do not delete or edit them while jobs are pending or running. Recovery
uses native lock ownership; entry age and PID are not reclaim authority.

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

## Python ownership

Filesystem operations live in storage/runtime adapters and the outer entrypoints.
Pure core identity, evaluation, redaction and DataFrame validation modules carry values
without reading or writing files. Application workflows route file operations through
explicit ports; report rendering writes its own owned artifacts through reporting
adapters. CLI composition initializes workspace policy before execution dependencies;
ordinary package imports do not initialize directories or configure global logging.
Programmatic callers select initialization and invocation ownership explicitly; see
[Python import migration](python-import-migration.md). These Python boundaries preserve
the destinations and cleanup rules in this document.

## Launch boundary

This policy routes application-owned writes and the named dependency storage needed for native
execution and publication; it is not an operating-system sandbox for arbitrary user-supplied
scripts or plugins. Python bytecode, external runners such as uv, pytest and pre-commit, and other
general dependency caches/configuration use their standard settings. A caller that needs broader
isolation must configure those tools in its launcher.

For queued model commands, the supervisor reads direct NVML inventory/process telemetry and uses a
metadata-only subprocess solely to map inherited `CUDA_VISIBLE_DEVICES` values to stable GPU UUIDs.
It waits without a ClearML task or native GPU context. An admitted fresh child receives assigned
UUIDs as its visible set and uses child-local native indices. Queue state remains outside run output
and owned temporary execution copies; child exit releases remaining reservations independently of
run-directory cleanup.

Existing caches are not migrated or deleted. Changing `CY_HOME` changes automatic paths;
explicit paths and read-only inputs remain independent of it.

## Explicit image deduplication

`cy-dedup [DIRECTORY] [--dry-run]` performs opt-in maintenance of an idle cache, defaulting
to `CY_HOME/.cache`. Same-named, byte-identical regular images may share filesystem blocks
using Linux reflinks. Paths and contents remain intact and subsequent writes are independent.
The command replaces a destination atomically through a temporary sibling, preserving its
mode, ownership, atime/mtime and extended attributes; inode, ctime and birth time can change.
Reads may update access times. Symlinks are excluded. Unsupported platforms/filesystems and
cross-device candidates are reported skips; unexpected I/O failures return nonzero.
Dry-run creates and replaces nothing. See the maintained
[deduplication contract](../specs/018-cache-image-dedup/contracts/cli.md) for file selection,
failure behavior and the idle-cache requirement.
