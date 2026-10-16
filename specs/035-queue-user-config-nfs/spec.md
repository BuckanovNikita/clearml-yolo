# Feature Specification: Per-user queue settings and NFS coordination

**Created**: 2026-10-16

**Status**: Delivered in 0.34.0

**Input**: Default queue configuration to the user's config directory and require every
queue user to fill it; remove the blanket library rejection of NFS coordination.
The target NFS is on another machine. No mount provisioning is requested here.

## User Scenarios & Testing

### User Story 1 - Configure each queue user (Priority: P1)

Each user fills a discoverable configuration file selecting the shared queue and
coordination paths. An explicit shared configuration override remains available.

**Independent test**: Resolve two different user config files that select the same
roots; reject missing/incomplete files before creating queue resources.

**Acceptance scenarios**:

1. Without an override, a filled config in the user's config directory is loaded.
2. An absolute explicit override wins, even when the default is missing or invalid.
3. Missing settings explain which file to create and which fields to fill; help works.

### User Story 2 - Select NFS coordination (Priority: P1)

An operator can select an eligible NFS coordination root instead of encountering
an unconditional library rejection, while retaining existing reservation guarantees.

**Independent test**: Simulated Linux mount records accept eligible NFS settings and
reject settings incompatible with the existing process-lifetime locking contract.

**Acceptance scenarios**:

1. NFS/NFSv4 with host-local flock, shared cache and reliable I/O is accepted.
2. Unsafe or indeterminate mount semantics are rejected with actionable guidance.
3. Existing binding conflicts and recovery records still prevent online relocation.

### Edge cases

Empty or relative XDG location; empty/relative explicit override; malformed TOML;
missing required keys; absent coordination directory; nested/escaped mountpoints;
missing mount fields; conflicting effective options; settings changed after launch.

## Requirements

- **FR-001**: Resolve explicit absolute `CY_QUEUE_CONFIG`, else absolute
  `$XDG_CONFIG_HOME/clearml-yolo/queue.toml`, else `$HOME/.config/clearml-yolo/queue.toml`.
  Empty/relative XDG is ignored; empty override means unset. Resolve the actual user
  home when HOME is unavailable. Do not search system config directories implicitly.
- **FR-002**: Require all existing TOML fields and absolute storage paths for every
  queue command except help. Fail missing/incomplete settings without creating files,
  storage or host bindings. Preserve explicit `--root` and legacy conflict checks.
- **FR-003**: Admit `nfs`/`nfs4` coordination only with effective `hard` and
  `local_lock=flock` or `local_lock=all`; reject `soft`, `softerr`, `nosharecache`
  and indeterminate local locking. Preserve existing local filesystem support.
- **FR-004**: Preserve ownership, frozen settings, host partitioning, protected
  binding, offline relocation and recovery. Never remove evidence automatically.
- **FR-005**: Update CLI help, queue contracts, user examples and portable usage
  guidance with configuration precedence, required settings and NFS operating limits.

### Key entities

Existing QueueSettings and TOML schema remain unchanged; only path selection and
filesystem eligibility change. No database, new daemon or dependency is introduced.

## Success Criteria

- **SC-001**: Default and override lookup tests pass, including two users sharing roots.
- **SC-002**: Eligible simulated NFS records pass; unsafe/unknown settings fail.
- **SC-003**: Existing coordination/recovery/process regressions and architecture gates pass.
- **SC-004**: Documented config/help examples run in isolation; real NFS evidence is
  explicitly unavailable, not inferred from simulated mount records.

## Assumptions

Linux only. Host participants share the same kernel NFS client/inode cache, mount and
PID namespaces and bootstrap. Distinct hosts retain distinct machine identities.
No live remount/replacement/relocation. Consistent UID mapping remains required.
Hard NFS can block filesystem calls during outages; local locks do not bound I/O.
No NFS installation, production migration, native GPU/ML change or SQLite conversion.
