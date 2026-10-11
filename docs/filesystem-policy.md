# Filesystem ownership

The eight application execution commands and `cy-init-config` establish a stdlib-only
runtime boundary before importing SDKs. Ordinary package imports remain inert. `CY_HOME` defaults to the launch working
directory; a relative value resolves once against that directory, and an absolute value
selects another project root. Later Hydra chdir does not change the captured root.
Explicit relative inputs/outputs retain their existing working-directory semantics.
`cy-dedup` loads no SDK configuration and does not initialize application directories
or alter library/process settings. Its atomic temporary files live beside the selected
destination and are cleaned there; optional TRACE remains local.

## Defaults and explicit destinations

| Content | Default beneath `CY_HOME` |
|---|---|
| Task-owned runs and latest shortcut | `runs/` |
| Hydra logs and sweeps | `outputs/`, `multirun/` |
| Shared CSV datasets | `.cache/clearml-yolo/datasets/` |
| Ultralytics downloaded datasets and weights | `.cache/ultralytics/datasets/`, `.cache/ultralytics/weights/` |
| Ultralytics settings | `.config/Ultralytics/` |
| ClearML downloads and cache | `.cache/clearml/` |
| ClearML session cache | `.cache/clearml/session/` |
| FiftyOne datasets, dataset zoo and database | `.cache/fiftyone/` |
| Owned execution copies, inference manifests and DDP relay/runtime files | `.tmp/` |

`dataset_cache_dir=null` selects `CY_HOME/.cache/clearml-yolo/datasets`, independent
of XDG. Explicit inputs, outputs and durable data/cache paths may live outside `CY_HOME`,
including `CLEARML_CACHE_DIR`, FiftyOne database/dataset/model directories and native
storage destinations. Existing data is neither migrated nor deleted. `HOME` is unchanged.

## Project library configuration

SDK configuration selectors must resolve physically inside `CY_HOME`; symlinks and
outside-project individual environment overrides are rejected. Ambient XDG search lists
are replaced; inherited XDG state selects shared queue coordination before being replaced
for SDK state. Ambient home/system configuration
is not read. Credentials come from explicit SDK environment values or ignored local
project configuration. Package defaults, installed binaries, certificates, fonts and
other OS runtime assets remain available. These rules cover exercised runtime libraries,
rather than imposing an OS sandbox on arbitrary user scripts/plugins.

| Configuration/cache selector | Automatic project location |
|---|---|
| `XDG_CONFIG_HOME`, `XDG_CONFIG_DIRS` | `.config` |
| `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `XDG_DATA_DIRS`, `XDG_STATE_HOME` | `.cache` and its `data`/`state` subdirectories |
| `YOLO_CONFIG_DIR` | `.config` (Ultralytics creates its settings beneath it) |
| `CLEARML_CONFIG_PATH`, `CLEARML_CONFIG_FILE` (and legacy `TRAINS_` aliases) | `.config/clearml`, `.config/clearml/clearml.conf` |
| Five FiftyOne config selectors | `.config/fiftyone/{config,app_config,annotation_config,evaluation_config,brain_config}.json` |
| FiftyOne plugins and ETA config | `.config/fiftyone/plugins`, `.config/eta` |
| Matplotlib/fontconfig selectors | `.config/matplotlib`, `.config/fontconfig` |
| Torch, Triton, CUDA, Numba, Hugging Face, Keras and Python bytecode | Named subdirectories of `.cache` |
| Requests `NETRC`, AWS config/credentials and `BOTO_CONFIG` | `.config/netrc`, `.config/aws`, `.config/boto.cfg` |
| `AWS_DATA_PATH` and botocore customer model overrides | `.config/aws/models` |

Optional `AWS_WEB_IDENTITY_TOKEN_FILE` and `AWS_CREDENTIAL_FILE` values must resolve
inside the project root. Bootstrap validates and normalizes these selectors without
creating files; supply any required credential file yourself. Scalar AWS environment
credentials remain explicit inputs. EC2/ECS metadata credential discovery is disabled.
The ClearML configuration adapter owns the SDK session-cache and botocore customer-model
constants, checks their supported interfaces before task creation and retains project
locations through SDK shutdown. Installed botocore model defaults remain available.
Every directory in an explicit `AWS_DATA_PATH` search list must also resolve inside
the project root.
Session state follows the validated XDG cache root and model overrides follow the
validated XDG configuration root. Both SDK directories are checked again for physical
containment, including nested symlinks, before creation.

FiftyOne selectors are `FIFTYONE_CONFIG_PATH`, `FIFTYONE_APP_CONFIG_PATH`,
`FIFTYONE_ANNOTATION_CONFIG_PATH`, `FIFTYONE_EVALUATION_CONFIG_PATH` and
`FIFTYONE_BRAIN_CONFIG_PATH`. Child-only compatibility redirects hardcoded home
paths before SDK import while preserving installed runtime assets. An unsupported
optional SDK layout warns and disables visualization. Matplotlib imports occur at a
project-config directory boundary to avoid launch-directory `matplotlibrc` precedence;
the launch directory is restored before resolving user input paths.
Explicit relative ClearML cache, FiftyOne data/database/model and ETA data/model paths
are normalized against the launch directory before this import context; environment
values take precedence over project FiftyOne data settings.
`ETA_MODELS_DIRS` accepts the existing comma/platform-separated input or a JSON array
of path strings. Use a JSON array when names contain delimiters. Bootstrap transfers
absolute paths as `CY_ETA_MODELS_DIRS` JSON and removes the ambiguous SDK selector;
the publication worker applies ETA's public configuration API before loading FiftyOne.
This preserves Windows drive letters and literal colons in directory names.

Shared GPU queue coordination is deliberately outside the project and `.tmp` arena.
Capture the original user-wide state root before installing XDG overrides:
`${XDG_STATE_HOME:-~/.local/state}/clearml-yolo/queue` on Unix-like systems or
`%LOCALAPPDATA%/clearml-yolo/queue` on Windows. Compatible registry/locks coordinate
projects; incompatible or corrupt state fails closed without migration/deletion.

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
owned temporary copies on success, failure or interruption. The invocation owns a unique
`.tmp/cy-runtime-*` arena with identity/liveness metadata and a lease. It scopes
`TMPDIR`, `TMP`, `TEMP` and `tempfile` through native children, optional publication,
upload completion and task finalization. Native DDP and publication children inherit
project settings and register their temporary ownership. Cleanup restores temporary
process settings and removes the arena only when owned participants are no longer live.
Abandoned recovery requires identity/liveness and lease evidence; PID or age alone is
insufficient. Cleanup failures and retained live ownership are explicit diagnostics.
Persistent datasets, caches, checkpoints, partial publication state and other jobs
are never treated as disposable scratch.

Atomic comparison cache publication uses temporary files beside the selected output so
rename remains atomic when the output is on another filesystem. These files are removed
on serialization, replacement or interruption errors as well as success. Other application-owned
temporary storage uses the owned `.tmp/` arena, including library temporary files.
A native worker with unsafe cleanup retains ownership; queue capacity cannot be released
while owned GPU descendants remain alive.

## Python ownership

Filesystem operations live in storage/runtime adapters and the outer entrypoints.
Pure core identity, evaluation, redaction and DataFrame validation modules carry values
without reading or writing files. Application workflows route file operations through
explicit ports; report rendering writes its own owned artifacts through reporting
adapters. CLI composition initializes workspace policy before execution dependencies;
ordinary package imports do not initialize directories or configure global logging.
Programmatic callers select initialization and invocation ownership explicitly.
`native_runtime()` also owns a runtime scope for direct native integrations, restoring
environment/temporary settings on exit; nested CLI scopes reuse invocation scratch. See
[Python import migration](python-import-migration.md). These Python boundaries preserve
the destinations and cleanup rules in this document.

## Launch boundary

This boundary governs exercised application/library configuration and temporary files.
External runners such as uv, pytest and pre-commit retain their own settings. Explicit
programmatic callers use `initialize_runtime_environment()` before SDK imports and
`runtime_environment()` around the entire invocation; see the
[Python migration example](python-import-migration.md#explicit-programmatic-dependencies).

GPU execution depends on independent queue/automatic-selection controls. Default queued
execution creates a supervised child with admitted UUID visibility. Direct automatic
execution preserves inherited visibility and executes in the caller after availability
waiting. Both controls false leaves native selection untouched without project GPU
telemetry. Shared coordination locks stay outside the arena. See the maintained
[execution contract](../specs/022-simple-gpu-wait/contracts/execution.md).

Existing caches are not migrated or deleted. Changing `CY_HOME` changes automatic paths
before SDK imports. Once an SDK retaining configuration is imported, the process remains
bound to that project even after scope exit; a different root requires a fresh process.
Explicit paths and read-only inputs remain independent of automatic defaults.

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
