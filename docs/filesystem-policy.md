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
| Invocation scratch | `.tmp/cy-runtime-*` |

`dataset_cache_dir=null` selects `CY_HOME/.cache/clearml-yolo/datasets`, independent of
XDG. `CY_RUNTIME_TEMP_ROOT` selects the parent of invocation arenas; its default is
`CY_HOME/.tmp`, and a relative selection resolves against `CY_HOME`. Explicit project
inputs, outputs, cache and temporary destinations may live outside the workspace,
including through symlinks. Existing data is neither migrated nor deleted.

Write destinations physically beneath the home directory warn once per resolved path
in a process. The requested path remains accepted. Symlinks determine the physical
destination: a link beneath home pointing outside it has an external destination.

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

Shared GPU queue coordination stays outside invocation scratch and remains user-wide:
`${XDG_STATE_HOME:-~/.local/state}/clearml-yolo/queue` on Unix-like systems or
`%LOCALAPPDATA%/clearml-yolo/queue` on Windows. An existing `CY_GPU_QUEUE_ROOT` stays selected.
Compatible registry/locks coordinate projects; corrupt or incompatible state fails closed
without migration or deletion. Bootstrap does not modify `XDG_STATE_HOME`.

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
is atomic across external output filesystems. The writer removes its own temporary sibling
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

Default queued execution creates a supervised child with admitted GPU UUID visibility.
Direct automatic execution waits for availability in the caller; both controls false
preserves native device selection without project telemetry. Shared coordination locks
stay outside arenas. See the
[GPU execution contract](../specs/022-simple-gpu-wait/contracts/execution.md).

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
