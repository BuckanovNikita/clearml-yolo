# Filesystem ownership

The application execution commands and `cy-init-config` initialize project paths through a
stdlib-only bootstrap. Ordinary package imports remain inert. `CY_HOME` defaults to the
launch working directory; relative values resolve against that directory before Hydra
changes cwd. Explicit relative inputs and outputs retain their working-directory semantics.
`cy-dedup` initializes no application directories or SDKs; its atomic temporary files live
beside the selected destination and are cleaned there.

## Defaults and explicit destinations

| Project-owned content | Default beneath `CY_HOME` |
|---|---|
| Task-owned runs and latest shortcut | `runs/` |
| Hydra logs and sweeps | `outputs/`, `multirun/` |
| Shared CSV datasets | `.cache/clearml-yolo/datasets/` |
| Invocation scratch and capture logs | `.tmp/cy-runtime-*` |
| Queue metadata (unless CY_QUEUE_ROOT is explicit) | `.cy-queue/` |
| Guardian diagnostics and progress | `.cy/queue-logs/`, `.cy/queue-status/` |

`dataset_cache_dir=null` selects `CY_HOME/.cache/clearml-yolo/datasets`, independent of
XDG. `CY_RUNTIME_TEMP_ROOT` selects the parent of invocation arenas; its default is
`CY_HOME/.tmp`, and a relative selection resolves against `CY_HOME`. Explicit inputs may live outside the workspace. Application-owned outputs, cache, logs,
configuration snapshots and temporary destinations must resolve beneath CY_HOME, including
through symlinks. Invalid destinations fail before creation. Existing data is neither migrated nor deleted.

Hydra preflight checks generated configuration files and log destinations using each
run's actual directory, including every sequential sweep member and the sweep manifest.
It resolves effective mode from both CLI flags and saved Hydra configuration.
Native trainers validate their selected existing output tree before creating checkpoints,
plots or logs; project checkpoint and metrics writers also validate their generated leaves.
Comparison ZIP archives validate both their selected directory and generated archive
filename before opening, including pre-existing symlinks.
These checks assume cooperating callers do not replace filesystem entries concurrently.

## Library configuration and storage

Libraries retain their ordinary environment, user configuration, cwd discovery and cache
policies. `HOME`, XDG selectors, ClearML and legacy Trains selectors, FiftyOne and ETA
selectors, Ultralytics settings, Matplotlib/fontconfig, Torch/Triton/CUDA/Numba, Hugging Face,
RF-DETR/Roboflow, Keras, Python bytecode, Requests/netrc and AWS configuration are unchanged.
AWS credential-provider discovery remains the SDK's responsibility. SDK selectors outside
`CY_HOME` are valid; bootstrap neither validates nor normalizes them, synthesizes config
files, substitutes private SDK constants, or changes cwd for imports. Relative selectors
therefore follow the selected library's own semantics.

Unresolved native checkpoint names and remote URIs pass through unchanged; libraries
determine download/cache locations. Existing local checkpoint strings are recognized as
`Path` inputs at their original locations, allowing local comparison without cache lookup.
The application does not redirect native dataset, weight or run defaults through global
Ultralytics settings. Its explicit training outputs and CSV-prepared data remain project-owned.

### Reuse earlier project-local library paths

Earlier versions selected SDK settings under `CY_HOME/.config` and caches under
`CY_HOME/.cache`. Those files remain available but are no longer automatically selected.
Opt in explicitly before SDK initialization, choosing only the libraries you want to reuse:

```bash
export CY_HOME="${CY_HOME:-$PWD}"
export CLEARML_CONFIG_FILE="$CY_HOME/.config/clearml/clearml.conf"
export CLEARML_CACHE_DIR="$CY_HOME/.cache/clearml"
export YOLO_CONFIG_DIR="$CY_HOME/.config"
export FIFTYONE_CONFIG_PATH="$CY_HOME/.config/fiftyone/config.json"
export TORCH_HOME="$CY_HOME/.cache/torch"
```

Select other SDK paths through their supported environment variables or user configuration.
Ensure selected files exist and contain valid settings; the application supplies no empty
placeholders or fallback configuration. It does not migrate or delete old settings, caches
or credentials. SDKs may cache their own settings after import; changing `CY_HOME` affects
project paths without rebinding those library settings.

`cy` does not initialize queue storage. The explicit `CY_QUEUE_ROOT` exception permits
shared NFS queue metadata outside the project; its default is `$CY_HOME/.cy-queue`.
Only small host coordination locks/claims live under `/tmp/clearml-yolo-queue`.
Datasets, checkpoints, logs and payloads never use that coordination directory.
Old home-based queues are neither migrated nor deleted. See [queue ownership](queue.md).

## Dataset cache and temporary ownership

Training prepares native inputs from `ground_truth` in the shared CSV-addressed cache.
Source images remain immutable. A cache consumer holds a native file lock through use;
unsupported native locks or acquisition errors fail clearly without a soft-lock fallback.
An existing invalid or incomplete entry is preserved and reported as an error. Inspect and
explicitly repair or remove that entry only while the cache is idle. Startup never sweeps
peer staging directories; preparation may remove its own unpublished staging after failure.

Project temporary callsites receive an explicit directory from `temporary_root()`.
Each invocation creates a unique `cy-runtime-*` arena; nested calls in the same process
reuse it, while spawned runtime scopes create separate arenas. Child processes may inherit
an arena reference. Resolved execution copies, manifests, DDP relay files, publication
protocol files and queue payloads use project-owned scratch. `TMPDIR`, `TMP`, `TEMP` and
`tempfile.tempdir` remain unchanged, so SDK temporary files follow ordinary library policy.

Invocation arenas are retained after success, failure, interruption and cancellation.
There are no owner/participant leases, startup scans, abandoned recovery or recursive arena
cleanup. A late child or another overlapping invocation may still use those files. Remove
selected retained scratch only through deliberate maintenance after confirming the relevant
workspaces and all descendants are idle; age, host or PID alone does not establish that.
Durable outputs, datasets, SDK caches and partial publication state remain persistent.

Atomic comparison publication uses a temporary sibling of its selected output so rename
is atomic within the selected project filesystem. The writer removes its own temporary sibling
on success or error. This bounded operation does not authorize sweeping an arena. Native
process cleanup remains required before releasing GPU capacity, regardless of retained files.

## Python and launch ownership

Storage/runtime adapters and entrypoints own filesystem effects. Pure core modules carry
values without reading or writing files; workflows use explicit ports. CLI composition
initializes project paths without configuring global logging or SDK storage. Programmatic
callers may use `initialize_runtime_environment()` and `runtime_environment()` explicitly;
see [Python import migration](python-import-migration.md#explicit-programmatic-dependencies).

`native_runtime()` scopes the ClearML enable switch and callbacks in memory, restores each
modified value on exit, and leaves the Ultralytics settings file untouched. Fresh DDP
trainers apply the worker callback scope during construction and training. Nested CLI use
reuses invocation scratch. Detector backends retain their normal configuration and caches.

Direct commands preserve native device settings without GPU admission. `cy-queue`
launches a fresh direct process with explicit UUID visibility and holds all capacity
until the complete pipeline and its descendants exit. See [queue ownership](queue.md).

## Explicit image deduplication

`cy-dedup [DIRECTORY] [--dry-run]` performs opt-in maintenance of an idle cache, defaulting
to `CY_HOME/.cache`. Same-named, byte-identical regular images may share filesystem blocks
using Linux reflinks. Paths and contents remain intact and subsequent writes are independent.
The command replaces a destination atomically through a temporary sibling, preserving its
mode, ownership, atime/mtime and extended attributes; inode, ctime and birth time can change.
Reads may update access times. Symlinks are excluded. Unsupported platforms/filesystems and
cross-device candidates are reported skips; unexpected I/O failures return nonzero.
Writable selections must remain beneath resolved `CY_HOME`; external selections are
permitted only with `--dry-run`, which creates and replaces nothing. See the maintained
[deduplication contract](../specs/018-cache-image-dedup/contracts/cli.md) for file selection,
failure behavior and the idle-cache requirement.
