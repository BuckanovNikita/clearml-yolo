# Feature Specification: Cache image deduplication

**Feature Branch**: `master` (existing release workflow)
**Created**: 2026-10-06
**Status**: Approved for implementation
**Input**: Add cy-dedup command that reflinks images under .cache by image_name.

## User Scenarios & Testing

### User Story 1 - Share duplicate image storage (Priority: P1)

A cache owner runs one maintenance command to share storage between repeated images
without changing their contents, names or independent-write behavior.
**Independent Test**: Duplicate equal images in separate directories, run the command,
and verify a successful reflink and independent subsequent writes.
**Acceptance**: Equal filenames and contents can share storage on supported filesystems;
same names with different contents and different names with equal contents remain intact.

### User Story 2 - Inspect candidates safely (Priority: P2)

A cache owner previews candidates and can run on filesystems without reflink support.
**Independent Test**: Dry-run leaves the directory unchanged; unsupported reflinks are
reported as skips, while unexpected I/O failures cause a nonzero exit.

### Edge Cases

Symlinks, hardlinked aliases, cross-device pairs, changed files, unreadable directories,
empty or missing roots, failed metadata restoration, and interrupted replacement.

## Requirements

- **FR-001**: Expose `cy-dedup [DIRECTORY] [--dry-run]`, defaulting to CY_HOME/.cache
  or the launch directory's .cache; do not initialize ClearML, GPU or application directories.
- **FR-002**: Recursively select regular images by documented extensions; exclude symlinks.
  Match exact case-sensitive filenames including extension and verify identical contents.
- **FR-003**: Share storage using reflinks with independent-write semantics. Preserve paths,
  contents, modes, ownership, timestamps and extended attributes during replacement.
- **FR-004**: Use deterministic sources; skip existing hardlinks and unsupported platforms,
  filesystems or cross-device pairs. Never substitute ordinary copies or hardlinks.
- **FR-005**: Preserve originals on failure or detected changes; clean temporary files on
  success, failure and interruption. Report unexpected I/O failures with nonzero exit.
- **FR-006**: Dry-run creates or replaces no files. Report scanned images, duplicates,
  successful reflinks, skips and failures without claiming measured physical savings.

## Key Entities

- Image candidate: path, exact basename, size, device, inode, content and metadata.
- Result: scanned/duplicate/reflinked/skipped/failure counts and diagnostic messages.

## Success Criteria

- **SC-001**: All unchanged eligible duplicates on a supporting filesystem become reflinks.
- **SC-002**: Content and protected metadata remain intact across successful replacements;
  failed replacements leave the original file in place.
- **SC-003**: Preview performs no creation/replacement; unsupported operations are explicit skips.

## Assumptions

`image_name` means filename, as selected by the user. Maintenance targets an idle cache;
it does not coordinate external writers or change normal cache creation. Linux initially
supports reflinking; other platforms report skips. Reading may update filesystem access
times. Replacing an inode changes its ctime and may change its birth time.
