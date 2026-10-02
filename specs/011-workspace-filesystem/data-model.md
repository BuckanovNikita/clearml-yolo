# Data model: Workspace-owned filesystem defaults

## Workspace

| Field | Meaning |
|---|---|
| `launch_directory` | Working directory observed before application dependencies import |
| `root` | Absolute `CY_HOME`, defaulting to `launch_directory` |
| `runs_root` | Automatic application outputs beneath `root/runs` |
| `cache_root` | Application dataset caches and named dependency data beneath `root/.cache` |
| `config_root` | Ultralytics settings beneath `root/.config/Ultralytics` |
| `temporary_root` | Owned invocation temporary storage beneath `root/.tmp` |

The workspace is captured once. Changing the process working directory does not mutate it.
General dependency cache/configuration and process temporary defaults are not workspace fields.

## Destination selection

| Field | Meaning |
|---|---|
| `requested` | Command value, dependency environment value, configured native value or default |
| `explicit` | Whether a caller selected the value rather than receiving a workspace default |
| `physical_target` | Existing-symlink-resolved destination used for home classification |
| `warned` | Process-local record preventing duplicate warnings for the same target |

An explicit selection remains authoritative regardless of location. Warning state changes only
diagnostics, never the selected path.

For `dataset_cache_dir`, `null` is an application default and resolves directly beneath
`cache_root` without consulting XDG. A non-null value is explicit. Existing FiftyOne
configuration may provide explicit dataset, dataset-zoo and database selections; the legacy
ClearML alias may provide its explicit cache selection.

## Native dataset entry

| Field | Meaning |
|---|---|
| `identity` | Stable digest of the checked definition and resolved text-manifest membership |
| `directory` | Workspace cache entry containing the final staged dataset |
| `yaml` | Staged definition rooted at the final entry |
| `images` | Owner-writable real copies preserving sorted membership, duplicates and source order |
| `labels` | Owner-writable annotation copies; absent labels represent negative images |
| `lock` | Per-entry ownership held through staging and native training |

Lifecycle: missing entry → private staging directory → atomic published entry → locked native
consumer → reusable entry. Failed staging removes the private directory.

## Owned temporary resource

| Field | Meaning |
|---|---|
| `owner` | Invocation or atomic output operation responsible for cleanup |
| `location` | Workspace `.tmp` by default, or beside an atomic publication destination |
| `purpose` | Execution configuration, inference manifest, DDP relay/runtime or partial output |
| `cleanup_boundary` | Context exit or `finally` block covering success, failure and interruption |

## Native runtime scope

The scope stores original Ultralytics directory settings, module-level path globals, callback
objects and `YOLO_CONFIG_DIR`. On entry it applies workspace defaults only to Ultralytics
downloaded datasets, weights, settings and runs where upstream defaults were active. On exit it
restores every stored value and deletes its owned temporary directory. Torch and other general
compute-library caches remain outside this scope.
