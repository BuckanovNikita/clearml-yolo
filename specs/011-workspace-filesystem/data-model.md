# Data model: Workspace-owned filesystem defaults

## Workspace

| Field | Meaning |
|---|---|
| `launch_directory` | Working directory observed before application dependencies import |
| `root` | Absolute `CY_HOME`, defaulting to `launch_directory` |
| `runs_root` | Automatic application outputs beneath `root/runs` |
| `cache_root` | Automatic dependency and application caches beneath `root/.cache` |
| `config_root` | Automatic dependency configuration beneath `root/.config` |
| `temporary_root` | Owned invocation temporary storage beneath `root/.tmp` |

The workspace is captured once. Changing the process working directory does not mutate it.

## Destination selection

| Field | Meaning |
|---|---|
| `requested` | Command value, dependency environment value, configured native value or default |
| `explicit` | Whether a caller selected the value rather than receiving a workspace default |
| `physical_target` | Existing-symlink-resolved destination used for home classification |
| `warned` | Process-local record preventing duplicate warnings for the same target |

An explicit selection remains authoritative regardless of location. Warning state changes only
diagnostics, never the selected path.

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
objects and `YOLO_CONFIG_DIR`. On entry it applies workspace defaults only where upstream defaults
were active. On exit it restores every stored value and deletes its owned temporary directory.
