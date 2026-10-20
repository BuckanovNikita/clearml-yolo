# Feature Specification: Evidence-backed cleanup and baseline reset

**Feature**: `037-cleanup-baseline` (work remains on the current authorized branch)

**Created**: 2026-10-20

**Status**: Approved for implementation

**Input**: Research the supplied OpenAI maintenance article, clean the code following its practices,
create a reusable personal cleanup skill, and consolidate all project task history into one
zero-stage specification with exact Git provenance. Include the existing uncommitted work.

## User Scenarios & Testing

### User Story 1 - Maintain supported behavior with less obsolete code (Priority: P1)

Maintainers can remove evidenced orphaned code without changing commands, configuration,
outputs, recovery, dependencies or operational safeguards.

**Independent Test**: Existing affected behavior and architecture tests pass after removal.

**Acceptance Scenarios**:

1. Given a candidate, when callsites, dynamic consumers and history are inspected, then
   removal requires evidence that no supported consumer remains.
2. Given an uncertain callback, serialization field or public interface, when an advisory
   scanner reports it, then it remains unless independent evidence proves retirement.

### User Story 2 - Start new work from one truthful baseline (Priority: P1)

Maintainers read current requirements and acceptance limits without replaying old task ledgers.

**Independent Test**: Every retired document is recoverable from an immutable checkpoint;
current documentation and tests resolve; next feature discovery selects 001.

**Acceptance Scenarios**:

1. Given uncommitted history, when consolidation runs, then it is committed before removal.
2. Given executable historical fixtures, when history is removed, then their original bytes
   and provenance remain in maintained test fixtures.
3. Given pending or waived obligations, when the baseline is written, then those dispositions
   remain distinct from executed verification and release.

### User Story 3 - Reuse the cleanup method (Priority: P2)

The personal cleanup-code skill supports evidence-backed maintenance across repositories.
History consolidation is an explicit optional operation, never an implicit cleanup side effect.

**Independent Test**: Package validation and independent realistic scenarios demonstrate
correct routing, evidence requirements, preservation and stopping conditions.

### Edge Cases

- Dynamic Hydra, worker, SDK and plugin consumers are not ordinary textual callsites.
- Current uncommitted cache changes have live acceptance and release gates outstanding.
- Historical numeric identities may recur after reset; provenance includes epoch and commit.
- Missing telemetry, capacity or required review remains a gap, not successful verification.

## Requirements

### Functional Requirements

- **FR-001**: Preserve supported behavior, approved dependencies, machine services and user work.
- **FR-002**: Record evidence and disposition for removed and retained candidates.
- **FR-003**: Preserve every retired document in a reachable immutable Git checkpoint.
- **FR-004**: Maintain one zero-stage specification with current contracts, provenance,
  limitations, pending work and instructions for fresh subsequent specifications.
- **FR-005**: Preserve test fixtures unchanged and migrate all live historical references.
- **FR-006**: Create, verify, release and install the reusable personal cleanup-code skill.
- **FR-007**: Complete applicable architecture, documentation, independent review and release gates.

### Key Entities

- Cleanup candidate: location, consumer/history evidence, disposition and verification.
- Historical checkpoint: immutable revision, retired paths and retrieval instructions.
- Baseline requirement: current behavior, authoritative guide, implementation/check evidence.
- Acceptance disposition: verified, pending, waived, superseded or released with limitations.

## Success Criteria

- **SC-001**: All selected removals preserve affected behavior and import contracts.
- **SC-002**: Every retired document is recoverable; both executable fixtures retain their hashes.
- **SC-003**: Current documentation resolves and next feature discovery selects 001.
- **SC-004**: The installed skill matches its checked and released source.

## Assumptions

The user approved repository-wide behavior-preserving cleanup, inclusion of existing work,
Git-only archival of all task history, a personal reusable skill and authorized release workflows.
Current maintained guides, governance, changelog, tooling and Git refs remain. Required unavailable
checks block acceptance/release; existing waivers are preserved rather than reopened.
