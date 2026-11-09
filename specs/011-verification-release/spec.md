# Feature Specification: Verification and Release Workflow

**Feature Branch**: `011-verification-release`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Migrate clearml-yolo developer verification and release to the
cveta2 model: one command owner for verification stages, a single development-verification
commit hook with staging and message guards, tiered live tests with a run-tag lifecycle,
changed-function mutation reports, two acceptance tiers, and a semantic-release flow under an
exclusive lock that replaces the local release script, while keeping weight releases, the paired
CY and cy-queue check and the digital-metrics pin unchanged."

Terms follow the "Verification and release" section of [GLOSSARY.md](../../GLOSSARY.md).
This feature changes contributor and release workflow only; product behavior in the
[baseline specification](../000-baseline/spec.md) is unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Development verification at commit time (Priority: P1)

A contributor (human or agent) changes code and commits. One named stage runs static checks
and the affected tests on the working copy. The commit is refused before any check runs when
tracked changes are left unstaged or nonignored untracked files exist, and when the message is
not a Conventional Commit.

**Why this priority**: Every change passes through it; it replaces the current per-tool hooks.

**Independent Test**: Commit a staged change with an unstaged sibling edit (refused), a bad
message (refused), and a clean staged change (development verification runs and passes).

**Acceptance Scenarios**:

1. **Given** staged and unstaged edits to tracked files, **When** committing, **Then** the commit
   is refused with guidance to stage inputs, and no files are stashed or changed.
2. **Given** a fully staged change, **When** committing with the message `update stuff`,
   **Then** message validation refuses the commit.
3. **Given** a fully staged code change, **When** committing, **Then** development verification
   runs lock, lint, import-boundary, type, dead-code and dependency checks plus affected tests,
   and does not build distributions or contact live services.
4. **Given** an explicitly skipped intermediate commit, **When** the final content is ready,
   **Then** the documented procedure requires development verification without skips.

---

### User Story 2 - Change acceptance on a clean tip (Priority: P1)

Before integration, a contributor runs change acceptance on a clean committed branch tip. It
runs all checks, property exploration, a bounded infrastructure preflight and the complete
suite including CPU live tests against the shared ClearML stand, with coverage held at or above
the recorded floor. Code changes also produce a mutation report for changed functions.

**Why this priority**: It is the gate for integration into `master`.

**Independent Test**: Run change acceptance on a dirty tree (refused), with the stand
unavailable (reported as deferred, exit distinct from failure), and on a clean tip with the
stand available (passes, run-tag resources cleaned).

**Acceptance Scenarios**:

1. **Given** uncommitted or untracked files, **When** change acceptance starts, **Then** it
   refuses before running checks.
2. **Given** the stand reports capacity wait or is unreachable within the preflight bound,
   **When** change acceptance runs, **Then** it stops with an "unavailable" outcome that is
   reported as deferred verification and blocks integration.
3. **Given** missing credentials or TLS trust, **When** preflight runs, **Then** it reports an
   error, not unavailability, and does not wait.
4. **Given** an available stand, **When** the live suite runs, **Then** all created objects carry
   one run tag and only that tag's objects are cleaned; incomplete cleanup is reported separately.
5. **Given** a documentation-only change, **When** accepted, **Then** the live part is not required.

---

### User Story 3 - Release under an exclusive lock (Priority: P1)

A maintainer with push authorization releases an accepted tip. Under one exclusive lock,
`master` fast-forwards to exactly that tip, the release tool computes the version from commit
history, writes version, changelog and the root lock entry, runs the release-commit check, and
creates the version commit and annotated tag. Push happens only when separately authorized.

**Why this priority**: Replaces the bespoke release script and fixes integration rules.

**Independent Test**: Rehearse in a throwaway worktree: compute the version, stage the version
commit with the release-commit check, confirm only the three permitted files and only the root
lock entry changed; discard without tagging or pushing.

**Acceptance Scenarios**:

1. **Given** another release holds the lock, **When** a release starts, **Then** it stops and
   reports the lock as a blocker without changing refs.
2. **Given** `master` cannot fast-forward to the accepted tip or the tip moved, **When**
   releasing, **Then** it stops and requires fresh acceptance.
3. **Given** the version commit stages any path other than `pyproject.toml`, `uv.lock` or
   `CHANGELOG.md`, or a `uv.lock` change outside the root package entry, **When** the
   release-commit check runs, **Then** it fails and no commit or tag is created.
4. **Given** only non-releasing commit types since the last tag, **When** releasing, **Then**
   no version is produced and this is reported as success.
5. **Given** no push authorization, **When** the release procedure reaches integration,
   **Then** it stops before changing `master`.

---

### User Story 4 - Release acceptance and paired release check (Priority: P2)

Before a version is delivered, release acceptance adds GPU-marked tests, FiftyOne checks, the
real-run gate on CPU and a single GPU, and the paired release check against the cy-queue
checkout at its configured location.

**Why this priority**: Required only at delivery, but blocks it.

**Independent Test**: Run the paired release check with the queue checkout missing (error), with
mismatched source and installed metadata (error), and with matching checkouts (passes and records
both commit identities and versions).

**Acceptance Scenarios**:

1. **Given** the GPU is busy with the user's workload, **When** release acceptance needs it,
   **Then** the GPU checks are deferred and block delivery.
2. **Given** a single-GPU host, **When** release acceptance runs, **Then** multi-GPU DDP is
   reported as waived and does not block.
3. **Given** a configured queue location, **When** the paired release check runs, **Then** it
   uses that location instead of the default sibling checkout.

---

### User Story 5 - Mutation report and session status (Priority: P3)

Contributors get a budgeted mutation report for functions changed against a base, with survivors
advisory and tool errors failing; and each agent session starts with a status report of branch
position, uncommitted paths, other worktrees, the release lock and any active run tag.

**Why this priority**: Improves evidence and concurrency safety; not a gate on its own.

**Independent Test**: Change one function and run the mutation stage (only that function's
mutants run); start a session with a held lock (status reports it).

**Acceptance Scenarios**:

1. **Given** no changed functions, **When** the mutation stage runs, **Then** it reports nothing
   to mutate and succeeds.
2. **Given** a clean-test failure inside the mutation copy, **When** it runs, **Then** it exits
   with a tool-error status distinct from surviving mutants.
3. **Given** any repository state, **When** the session status report runs, **Then** it never
   fails the session start.

### Edge Cases

- Interrupted live run leaves an active run tag: a new run refuses until it is stopped or adopted.
- Stand availability disappears during setup: blocked setup, not a test failure; assertions after
  setup remain test failures.
- Inherited shared environment or cache overrides: stages still use this worktree's environment
  and tool state.
- Interpreter, lock, configuration or file-membership change: affected-test selection starts a
  fresh baseline rather than reusing stale history.
- Tests that need serial execution (CPU DDP, process supervision, live) run serially while others
  run in parallel; a reported random-order seed reproduces a failure.
- A failed release attempt leaves staged version files without a commit: recovery restores only
  that attempt's changes; versions and tags are never hand-edited.
- External source trees missing when the lock is refreshed: the release stops with an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One command owner MUST define named stages for fix, development verification,
  affected tests, full tests, property exploration, mutation report, infrastructure preflight,
  live integration, change acceptance, release acceptance, paired release check and release-commit
  check. Stage completion MUST NOT be inferred from cached freshness.
- **FR-002**: Every stage MUST use the current worktree's environment, affected-test history,
  coverage data and tool caches, overriding inherited shared locations.
- **FR-003**: Development verification MUST run lock freshness, lint and format checks, import
  boundaries, type checks, dead-code checks, declared-dependency checks and affected tests, and
  MUST NOT build distributions or contact live services.
- **FR-004**: The fix stage MUST apply only safe lint fixes and formatting and MUST NOT stage files.
- **FR-005**: The pre-commit hook MUST run development verification serially and MUST refuse
  commits with unstaged tracked changes or nonignored untracked files before any stashing.
- **FR-006**: Commit messages MUST be validated against the Conventional Commit types the
  project allows.
- **FR-007**: Heavy stages (live integration, change acceptance, property exploration, mutation)
  MUST be manual, never automatic on commit.
- **FR-008**: Affected-test selection MUST use a history namespace derived from interpreter,
  locked dependencies, verification configuration, test fixtures and tracked file membership.
- **FR-009**: Live tests (GPU DDP, Severstal GPU, FiftyOne and ClearML-stand tests) MUST live in a
  dedicated directory, be marked as integration, and be excluded from development verification
  and affected-test runs by location.
- **FR-010**: Live runs MUST pass a read-only preflight bounded by a configurable timeout with
  distinct available, unavailable and error outcomes; preflight MUST NOT create tags or resources.
- **FR-011**: Each live run MUST use one run tag for all created objects, refuse to start while
  another run tag is active in the worktree, and clean only objects carrying its exact tag,
  reporting incomplete cleanup.
- **FR-012**: Unit tests MUST run in parallel with a configurable worker count, keep CPU DDP,
  process-supervision and live tests in serial groups, randomize order with a reported
  reproducible seed, isolate home, configuration and Git environment, and provide default
  deterministic and exploration property-testing profiles.
- **FR-013**: Change acceptance MUST require a clean committed tip before and after running and
  MUST run checks, property exploration, preflight and the complete suite with coverage at or
  above the recorded floor; documentation-only changes MAY omit the live part.
- **FR-014**: Release acceptance MUST add GPU-marked tests, FiftyOne checks, the documented
  real-run gate on CPU and a single GPU, and the paired release check.
- **FR-015**: Unavailable stands, capacity wait and a GPU busy with the user's workload MUST be
  reported as deferred verification and block acceptance, integration and release. User-waived
  checks (multi-GPU DDP on single-GPU hosts) MUST be reported as waived and MUST NOT block.
- **FR-016**: The paired release check MUST locate cy-queue from a configurable location
  defaulting to the sibling checkout, fail on a missing checkout, dependency conflict or
  source/installed metadata mismatch, run the queue suite and command help, and record both
  commit identities and versions.
- **FR-017**: The release tool MUST alone determine versions, changelog entries and annotated
  `v{version}` tags from Conventional Commits, with breaking changes below 1.0 bumping minor.
- **FR-018**: The release-commit check MUST permit staged changes only to `pyproject.toml`,
  `uv.lock` and `CHANGELOG.md`, MUST reject `uv.lock` changes outside the root package entry,
  and MUST re-run lock freshness, read-only lint/format and dependency checks.
- **FR-019**: Integration and release MUST hold one exclusive per-repository release lock from
  fast-forwarding `master` to the accepted tip through tagging and any authorized push; a held
  lock MUST be reported, not waited on or broken.
- **FR-020**: Pushing `master` and tags MUST require separate authorization; without it the
  release procedure MUST stop before integration.
- **FR-021**: The local release script and its recovery record MUST be removed; recovery of a
  failed attempt MUST be documented in the release procedure.
- **FR-022**: The mutation stage MUST mutate only functions changed against the staged index or a
  named base, within a configurable function and time budget, with exit statuses distinguishing
  success, strict survivors and tool errors; survivors are advisory by default.
- **FR-023**: An agent session-start report MUST show branch position relative to `master`,
  uncommitted paths, other worktrees, release-lock state and active run tag, and MUST never fail.
- **FR-024**: Model-weight releases, the digital-metrics pin and the prohibition on building
  distributions for releases MUST remain unchanged.
- **FR-025**: Development procedures, DDP testing guidance, agent instructions, contributor skills
  (verification workflow, release, mutation testing, running integration tests), the Russian
  README developer section, the constitution's verification principle and an ADR for the release
  mechanism and acceptance tiers MUST describe the new workflow; stale passages MUST be removed.

### Key Entities

- **Verification stage**: A named, invocable step with defined inputs and outcome
  (passed, failed, deferred, waived, error).
- **Run tag**: Identity carried by every object a live run creates; scope of cleanup.
- **Release lock**: Exclusive per-repository marker held from integration through tagging.
- **Version commit**: The release tool's commit carrying version, changelog and root lock entry.
- **Coverage floor**: Recorded minimum coverage, set from the measured value at adoption.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of refused commits (unstaged inputs, untracked inputs, invalid message) leave
  the working tree and index byte-identical to before the attempt.
- **SC-002**: A one-file code change completes development verification without running any
  live test or distribution build.
- **SC-003**: Release rehearsal changes exactly three files and exactly one lock entry.
- **SC-004**: Every live run leaves zero objects carrying its run tag after successful cleanup.
- **SC-005**: Unavailable infrastructure is reported within the preflight bound (default 60
  seconds) and never as a pass.
- **SC-006**: Contributors invoke every documented verification and release step through one
  command owner; no procedure document references the removed release script.

## Assumptions

- No CI is introduced; verification remains local, as in cveta2.
- Scripts are copied and adapted from cveta2, not shared as a package.
- The coverage floor is the value measured on the branch before tightening; it is recorded in
  configuration, not in instructions.
- Live-run tags and stand access reuse the existing environment scripts and k8s-infra tooling.
- Multi-GPU DDP remains waived on this host by standing user decision.
- Work happens on branches or worktrees; `master` only moves by fast-forward.
