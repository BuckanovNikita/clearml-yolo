# Feature Specification: Readable shared queue

**Created**: 2026-10-16

**Status**: Approved for implementation

**Input**: User-approved readable output, reversible archive, explicit shared file-store
configuration, and real two-user verification. Temporary local test accounts and cleanup
are authorized. Production deployment is outside this change.

## User Scenarios & Testing

### User Story 1 - Read meaningful output (Priority: P1)

Operators identify jobs, models and sources by names rather than opaque identifiers.
Independent test: capture CLI/TUI, errors, reports and forwarded native console output.

1. A submitted job displays its stable submission number and task/explicit label.
2. Reordering or archiving never changes that number; commands accept job-number references.
3. Human output contains no UUIDs, task identifiers or digest strings; machine metadata
   and explicit JSON retain exact public job, host and boot identifiers and task-link
   targets. Existing GPU JSON fields retain display aliases and secret exclusion.
4. Reports preserve metric values and source provenance while displaying readable names.

### User Story 2 - Archive obsolete jobs (Priority: P2)

Owners hide finished jobs for all viewers and can restore them without deleting history.
Independent test: archive/restore through real storage and verify CLI/TUI visibility.

1. Completed, failed and cancelled jobs can be archived by their effective Unix owner.
2. Main views exclude archives; archive/all views include them with readable references.
3. Active and recovery-required jobs cannot be hidden. A later recovery requirement
   makes an archived job visible again.
4. Archive never changes outcomes, reservations, ordering history or job numbering.

### User Story 3 - Share one configured queue (Priority: P1)

Two Unix users load one shared configuration and operate the same host queue.
Independent test: run actual subprocesses with two temporary effective users.

1. Missing configuration fails with setup guidance instead of creating a project queue.
2. Shared metadata and coordination settings propagate to workers and guardians.
3. Both users can read summaries and reorder pending jobs; private snapshots/logs remain
   owner-only and ownership governs cancellation, recovery and archive changes.
4. Conflicting host coordination locations fail before admission; separate project
   workspaces retain their own execution logs and progress files.

### Edge Cases

Duplicate/empty/Unicode labels, opaque names supplied by users, IDs inside URLs or paths,
partial UTF-8/identifier stream chunks, restrictive umasks, interrupted archive writes,
stale revisions, archived references, corrupt sidecars, incompatible existing workers,
missing configuration and unavailable privileges. Preserve all original diagnostic bytes.

## Requirements

- **FR-001**: Use names and stable job-number references in all human output, including
  messages, TUI, report/chart/table captions and forwarded console text.
- **FR-002**: Preserve exact machine identities, provenance, raw capture and metric values;
  provide explicit JSON command output while accepting legacy identifier inputs.
- **FR-003**: Implement owner-only reversible archive for terminal jobs, main/archive/all
  visibility, idempotence and complete unfiltered scheduling/history.
- **FR-004**: Require a shared configuration selected through an environment variable,
  defining queue name, metadata root and host-local coordination root with no implicit fallback.
- **FR-005**: Preserve cross-user ownership, cross-root device exclusion and explicit
  setting propagation through every queue process and transaction.
- **FR-006**: Verify real separate-user permissions, concurrency, worker behavior and
  cleanup using task-owned temporary accounts and fixtures.
- **FR-007**: Update contracts, README, portable usage skill, architecture enforcement
  and dated verification before independent review and the authorized native release.

### Key Entities

Readable job reference; original model identity; archive visibility record; resolved
queue settings; owner-private snapshot; shared host coordination binding.

## Success Criteria

- **SC-001**: Tested human views never expose opaque identities, including failure paths.
- **SC-002**: Stable job references survive reorder, archive and restart without mis-targeting.
- **SC-003**: Two real users share summaries/order but cannot access private data or perform
  owner-restricted operations on another user's jobs.
- **SC-004**: Required behavior, architecture, documentation and review checks pass;
  test accounts and processes are removed and remaining limits reported accurately.

## Assumptions

Keep the current file store, dependency pins, effective UID model and Linux platform.
No database migration, persistent privileged service or production configuration change.
User-facing text changes intentionally supersede historical full-ID display requirements.
Keep execution logs/progress in submitting projects. Explicit JSON is machine output.
