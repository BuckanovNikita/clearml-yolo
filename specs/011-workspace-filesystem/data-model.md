# Data model: Workspace-owned filesystem defaults

## Workspace

| Field | Meaning |
|---|---|
| `launch_directory` | Working directory observed before application dependencies import |
| `root` | Absolute `CY_HOME`, defaulting to `launch_directory` |
| `runs_root` | Automatic application outputs beneath `root/runs` |
| `cache_root` | Application CSV dataset cache beneath `root/.cache/clearml-yolo/datasets` |
| `temporary_root` | Explicit `CY_RUNTIME_TEMP_ROOT`, default `root/.tmp`; relative selectors resolve against `root` |

Initialization normalizes `CY_HOME` before working-directory changes. Later cwd changes
do not mutate it; an explicit new `CY_HOME` selects new project paths without rebinding SDK
settings. Library configuration/cache and process temporary defaults are not workspace fields.

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
configuration may provide explicit dataset, dataset-zoo and database selections;
`CLEARML_CACHE_DIR` may provide an explicit ClearML cache selection.

## Prepared dataset entry

| Field | Meaning |
|---|---|
| `identity` | Stable digest of CSV bytes, selected format and preparation version |
| `directory` | Workspace cache entry containing the complete prepared dataset |
| `ground_truth` | Validated cleaned CSV used by later stages |
| `data` | Prepared NDJSON or flat native training reference |
| `lock` | Per-entry ownership held through preparation and training |

Lifecycle: missing entry → private preparation directory → atomic complete entry → locked
consumer → reusable entry. Failed preparation is never consumed. Existing invalid entries
are preserved with an error and require deliberate idle maintenance. Peer staging is never
swept; only the builder's own unpublished staging may be removed after failure. Native lock
failures have no soft-lock fallback.

## Project temporary resource

| Field | Meaning |
|---|---|
| `owner` | Invocation or atomic output operation creating the file/directory |
| `location` | Explicit invocation arena, or sibling of an atomic publication destination |
| `purpose` | Execution config, manifest, DDP relay, queue payload, worker protocol or partial output |
| `retention` | Invocation arenas survive every exit outcome; a writer cleans only its own atomic temporary sibling |

Arenas are unique per runtime process; nested scopes reuse them. There are no owner/participant
leases, startup scans or abandoned recovery. Idle maintenance is explicit and requires all
relevant descendants to be idle, independently of file age/host/PID.

## Native runtime scope

The scope stores the in-memory Ultralytics ClearML enable switch, callback objects and
associated integration attributes. It enables callbacks for the invocation owner, suppresses
worker ownership and restores every modified value without persisting settings. Fresh DDP
trainers scope construction and training explicitly. Native directories, SDK configuration,
user settings, caches, cwd and global temporary defaults retain their normal policy.
Earlier local library settings/cache files remain on disk and require explicit SDK selection.
