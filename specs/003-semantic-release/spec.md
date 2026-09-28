# Feature Specification: Local Semantic Release

**Feature Branch**: `master`

**Created**: 2026-09-28

**Status**: Implemented; see [dated verification](../../docs/evidence/2026-09-28-semantic-release.md)

**Input**: Integrate semantic release using the existing Spec Kit workflow. Use local
hooks and tags only, automatically after commits, with package version updates and
continued 0.x versioning.

## User Scenarios & Testing

### User Story 1 - Automatic local versioning (Priority: P1)

A contributor commits a fix, feature, or breaking change on master and receives a
checked version-update commit and annotated version tag without a separate release command.

**Why this priority**: Removes manual version arithmetic and inconsistent package metadata.

**Independent Test**: Commit each release category in a temporary repository starting
at v0.3.0; inspect the resulting commit, metadata, and tag.

**Acceptance Scenarios**:

1. **Given** v0.3.0, **when** a fix is committed, **then** the version becomes 0.3.1.
2. **Given** v0.3.0, **when** a feature or breaking change is committed, **then** the
   version becomes 0.4.0 and remains below 1.0.
3. **Given** only non-release changes since the last tag, **when** committed,
   **then** no version commit or tag is created.

### User Story 2 - Preserve contributor work (Priority: P1)

Contributors can use normal branches, partial commits, and existing quality checks
without the release automation overwriting work or bypassing failures.

**Why this priority**: Hook automation must not compromise source history or local changes.

**Independent Test**: Exercise dirty files, staged changes, rejected release commits,
feature branches, detached HEAD, and competing invocations in temporary repositories.

**Acceptance Scenarios**:

1. **Given** unrelated tracked changes, **when** the hook runs, **then** release work
   is deferred with an explanation and existing changes remain intact.
2. **Given** a failing quality hook, **when** the release commit is attempted,
   **then** no version tag is created and the user's original commit remains.
3. **Given** a feature branch or history rewrite, **when** the hook runs,
   **then** it does not change metadata, history, or tags.

### User Story 3 - Recover a local release (Priority: P2)

A contributor can retry an interrupted release without producing duplicate commits
or replacing existing tags.

**Why this priority**: Post-commit failures occur after the original commit is saved.

**Independent Test**: Fail tag creation after a successful version commit, retry,
and verify exactly one release commit and one tag.

**Acceptance Scenarios**:

1. **Given** a completed version commit without its tag, **when** retried,
   **then** that same commit is tagged after its checks pass.
2. **Given** an already completed release, **when** retried,
   **then** history and tags remain unchanged.
3. **Given** a conflicting version tag, **when** retried,
   **then** the conflict is reported and the existing tag is preserved.

### Edge Cases

- Dirty index or tracked worktree, shallow history, missing baseline tag, detached
  HEAD, rebase/cherry-pick in progress, tag collisions, and simultaneous worktrees.
- Nested release commit hooks, stale recovery state, interrupted metadata updates,
  failed dependency lock refresh, failed quality hooks, or failed tag creation.
- Existing untracked files remain untouched; a later retry requires inspection of
  retained release edits before they are committed.

## Requirements

### Functional Requirements

- **FR-001**: Automate local releases only on master after successful commits.
- **FR-002**: Derive the next version from Conventional Commits since the latest
  reachable version tag; fixes/performance changes increment patch, features and
  breaking changes increment minor while the major version is zero.
- **FR-003**: Keep package and lockfile versions aligned in one follow-up
  `chore(release): VERSION` commit, then annotate that commit with `vVERSION`.
- **FR-004**: Retain all existing commit checks for the generated commit and prevent
  recursive or concurrent release operations.
- **FR-005**: Preserve unrelated files, existing tags, original commits, external
  dependency sources, and locked dependency versions.
- **FR-006**: Skip unsupported branches/history operations and defer dirty-tree
  releases before modifying tracked files; report actionable failures.
- **FR-007**: Provide an idempotent local retry command, including recovery after a
  completed release commit whose tag failed.
- **FR-008**: Do not build distributions, create changelogs, publish releases,
  push, fetch, or introduce CI/CD. Installing hooks must not release anything.
- **FR-009**: Document setup, commit categories, failure recovery, and manual tag
  pushing in the Russian README; retain the nine application entrypoints.

### Key Entities

- Release candidate: source commit, previous reachable tag, computed next version.
- Release commit: only package-version metadata and its matching lockfile update.
- Version tag: immutable annotated reference to the checked release commit.
- Local operation: exclusive lock and recoverable attempt metadata, outside tracked files.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every supported release category produces the expected version and
  exactly one checked metadata commit and annotated tag in acceptance fixtures.
- **SC-002**: Negative and recovery scenarios preserve all unrelated work and
  existing tags; repeated successful operations create no additional changes.
- **SC-003**: The complete local workflow requires no remote credentials or service
  access after development dependencies are installed.
- **SC-004**: Repository checks and temporary-repository hook scenarios pass; no
  real release is created merely to verify this integration.

## Assumptions

- Contributors install development dependencies and hooks in each clone.
- Tags are local version markers, not evidence of GPU or ClearML release validation.
- The first eligible invocation includes existing unreleased history after v0.3.0.
- Routine non-release types do not cause a bump; all eligible history is considered
  when earlier releases were deferred. Promotion to 1.0 is deliberate configuration work.
- Acceptance verification uses temporary repositories; creating a release, pushing,
  and publication in the main checkout are separate authorized operations.
