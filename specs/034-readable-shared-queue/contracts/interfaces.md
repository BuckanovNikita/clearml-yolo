# Readable output and queue interfaces

## Shared settings

`CY_QUEUE_CONFIG` names an absolute TOML file with `[queue]` keys `name`, `root`,
`coordination_root`; both directories are absolute. No implicit metadata fallback.
`--root` explicitly overrides metadata; legacy CY_QUEUE_ROOT must agree with the selected
root. `cy-queue config [--json]` is read-only. Help requires no configured queue.
Workers/guardians use resolved values. Host binding rejects conflicting coordination roots.

## Commands and presentation

Submit accepts `--label`; task name supplies the default. Text shows `Job N · label`.
Queue actions accept `job-N` or legacy internal keys; text never echoes opaque keys.
Commands returning machine data support explicit `--json`, preserving exact public IDs.
The existing GPU contract is retained: GPU fields use physical indexes or stable word
aliases even in JSON; claim tokens and private fields remain excluded. Human message
fields in JSON remain formatted, while job, host, boot and task-link identities are exact.
List and TUI default to main; `--archived` and `--all` are mutually exclusive modes.
Archive/restore accept one or more references, validate targets before changing a batch,
and are idempotent and owner-only. Only completed/failed/cancelled may be archived.
TUI relative movement selects a readable job, preserving snapshot revision validation.

User messages, errors, console, report banners and table/chart captions use readable
names/roles. URLs may remain exact link targets but cannot appear as opaque text.
Known physical GPUs use indexes; unavailable GPUs use deterministic word aliases.
Keep exact IDs in explicit JSON/provenance/hidden workbook identity and original logs.

## Preservation

Archive is not a state transition, deletion, cancellation or reservation release.
All scheduling/replay uses full history; visible recovery requirements override archive.
Unix ownership and private-project log/progress boundaries remain enforced.
Streaming transforms cannot alter captured bytes, scalar numeric values or acknowledgements
of source offsets; pending fragments are included at final flush without unbounded buffering.
