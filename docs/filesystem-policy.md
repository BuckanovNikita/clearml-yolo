# Filesystem ownership

The application execution commands, `cy-batch-estimate`, `cy-download-weights` and `cy-init-config` initialize project paths through a
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
| Training batch estimates | `.config/clearml-yolo/batch-estimates.json` |
| Managed DEIM weights and legacy compatible assets | `.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>` |
| Managed DEIM source archive and tree | `.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz` and adjacent `<revision>/` |
| Model preparation receipts and locks | `.cache/clearml-yolo/preparation/` |
| Invocation scratch and capture logs | `.tmp/cy-runtime-*` |
| Guardian diagnostics and progress | `.cy/queue-logs/`, `.cy/queue-status/` |

`dataset_cache_dir=null` selects `CY_HOME/.cache/clearml-yolo/datasets`, independent of
XDG. `CY_RUNTIME_TEMP_ROOT` selects the parent of invocation arenas; its default is
`CY_HOME/.tmp`, and a relative selection resolves against `CY_HOME`. Explicit inputs may live outside the workspace. Application-owned outputs, cache, logs,
configuration snapshots and temporary destinations must resolve beneath CY_HOME, including
through symlinks. Invalid destinations fail before creation. Existing data is neither migrated nor deleted. Native model asset publication is the
specific exception described below; it does not relax project destination checks.

The unreleased [batch estimator](batch-estimation.md) uses a versioned JSON catalogue
with a native file lock and atomic replacement beneath `CY_HOME`. It records successful
and failed cases, diagnostics and provenance without creating a ClearML task. Its
configuration location is independent of queue configuration discovery.

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
selectors, Ultralytics configuration roots, Matplotlib/fontconfig, Torch/Triton/CUDA/Numba, Hugging Face,
RF-DETR/Roboflow, Keras, Python bytecode, Requests/netrc and AWS configuration are unchanged.
AWS credential-provider discovery remains the SDK's responsibility. SDK selectors outside
`CY_HOME` are valid; bootstrap neither validates nor normalizes them, synthesizes config
files, substitutes private SDK constants, or changes cwd for imports. Relative selectors
therefore follow the selected library's own semantics.

Ultralytics checkpoint names and remote URIs retain native semantics. Explicit native
[model preparation](model-assets.md) populates effective Ultralytics, Torchvision,
timm/HF and RF-DETR caches, even when those native roots are outside `CY_HOME`.
Only model asset publication, its locks, temporary sibling downloads and native HF
metadata use this exception. Explicit preparation and YOLO batch-estimator setup
also persist an absolute Ultralytics `weights_dir`, resolving a relative value
against the invocation cwd and retaining an existing absolute destination. CY uses
an adjacent settings-file lock, verifies the persisted mapping and synchronizes
live SDK `weights_dir` and `WEIGHTS_DIR`; correct repeated calls do not rewrite it.
Unrelated disk settings, process-only switches, cache files and native dataset/run
defaults are preserved. Imports, help and configuration inspection remain inert.
See [cache migration and recovery](model-assets.md#cache-locations) for a one-time
rerun from the original preparation directory and settings-file/permission errors. DEIM source/weights, durable preparation receipts,
application outputs and CSV-prepared data remain project-owned beneath `CY_HOME`.
Explicit local inputs remain authoritative. Existing local checkpoint strings are
recognized as `Path` inputs at their original locations, allowing local comparison
without cache lookup. Relative inputs follow the consuming process's cwd.

### Managed model assets

Asset identities incorporate canonical source, revision and available checksum.
The resolver checks valid local/cache files before proxy and upstream requests.
Per-asset locks, temporary sibling downloads and atomic publication keep concurrent
consumers from observing incomplete files. DEIM extraction rejects unsafe archive
entries and verifies code/configuration against the packaged approved manifest.
Manually placing the exact files or source archive at the paths in an error message
is sufficient for offline reuse; an earlier online receipt is not required.
Canonical replay retains input selectors. The separate `model_assets` ClearML
Configuration Object records resolved paths, original URLs and content hashes. See [offline recovery](model-assets.md#offline-placement-and-access).

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

CY execution, including ClearML Agent replay, does not initialize queue storage.
The separate `cy-queue` package retains the existing locations and namespaces;
its extraction does not relocate files. Each queue user must fill the TOML file at
`$XDG_CONFIG_HOME/clearml-yolo/queue.toml` (absolute XDG_CONFIG_HOME), otherwise
`~/.config/clearml-yolo/queue.toml`; explicit absolute `CY_QUEUE_CONFIG` overrides it.
The required name, shared metadata `queue.root` and `queue.coordination_root` have no
implicit defaults and neither storage path derives from `CY_HOME`. Metadata may use
NFS; coordination accepts local Linux filesystems or NFS/NFSv4 with effective
`hard,local_lock=flock` (or `all`) and shared cache, subject to the
[NFS operating requirements](queue.md#nfs-coordination). The fixed bootstrap
namespace under `/tmp/clearml-yolo-queue` binds each host to its configured location.
`--root` overrides metadata only; legacy `CY_QUEUE_ROOT` must agree. New shared roots
have explicit sticky permissions; existing roots and parents retain their modes.
Private snapshots remain owner-only in the queue; logs and progress stay in each
submitting project's directories. Archive sidecars affect visibility without deleting
any execution evidence. See [configuration and relocation](queue.md#shared-configuration).
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
reuses invocation scratch. Detector backends retain their normal SDK configuration;
managed asset paths are supplied through execution-only model copies, not global
cache changes.

Direct commands preserve native device settings without GPU admission. `cy-queue`
launches a fresh direct process with explicit UUID visibility. It retains the full
training allocation until acknowledged contraction; the first GPU remains reserved
through command/descendant exit unless explicitly freed. See [queue ownership](queue.md).

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
[deduplication contract](../specs/000-baseline/spec.md#explicit-cache-deduplication) for file selection,
failure behavior and the idle-cache requirement.
