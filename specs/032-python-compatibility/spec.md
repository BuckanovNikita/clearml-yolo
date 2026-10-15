# Feature Specification: Python 3.12 and 3.13 compatibility

**Feature Branch**: `master`

**Created**: 2026-10-15

**Status**: Implemented, accepted and released as v0.30.0

**Input**: Allow Python `>=3.12.13,<3.14` for clearml-yolo. Keep the canonical
checkout on its existing primary branch. Companion projects cveta2 and ed-killer
use `>=3.12,<3.14` in their own repositories.

## User Scenarios & Testing

### User Story 1 - Install with either supported minor version (Priority: P1)

An operator can install and invoke the application using Python 3.12.13 or later
in the 3.12 series, or a Python 3.13 release, without changing application settings.

**Independent Test**: Install the built wheel in separate supported environments,
invoke configuration/queue help and run the existing process-supervision probe.

**Acceptance Scenarios**:

1. Given Python 3.12.13 or 3.13, installation metadata accepts the interpreter and
   ordinary command/configuration behavior remains available.
2. Given Python 3.12.12 or 3.14, installation metadata rejects the interpreter.
3. Given an accepted Python version without required Linux pidfd capabilities,
   native execution still fails before starting model work.

### Edge Cases

Python patch versions do not identify the standalone distribution build. A matching
version range does not guarantee pidfd, kernel, driver or optional backend support.
Existing queued snapshots retain their interpreter and installation identity.

## Requirements

- **FR-001**: Package metadata and the lockfile must declare `>=3.12.13,<3.14`.
- **FR-002**: Existing application behavior, dependency source revisions and import
  boundaries must remain unchanged; dependency updates unrelated to compatibility
  are excluded.
- **FR-003**: Maintained installation guidance must state the supported range and
  distinguish interpreter version from required process-supervision capabilities.
- **FR-004**: Verification must cover both supported minor versions and the built
  package, with unavailable native/GPU evidence reported accurately.

## Success Criteria

- **SC-001**: Every accepted/rejected version boundary in User Story 1 agrees with
  built package metadata.
- **SC-002**: Existing regression checks and installed command checks pass on both
  supported minor versions, or any acceptance gap is explicitly recorded.
- **SC-003**: Documentation and release delivery reflect the final compatibility
  contract while preserving unrelated local work.

## Assumptions

- The development interpreter remains Python 3.12; the compatibility range is wider.
- No unsafe supervision fallback, dependency-source change or model algorithm
  change is authorized by this packaging request.
- Existing branch names and Git-tag-only release policies remain in force.
