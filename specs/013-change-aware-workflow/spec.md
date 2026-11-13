# Feature Specification: Change-aware verification and simpler workflow tooling

**Feature Branch**: `013-change-aware-workflow`
**Created**: 2026-11-13
**Status**: Approved intent
**Input**: User-supplied implementation plan, “Simplify workflow tooling and make verification change-aware”.

## User Scenarios & Testing

### User Story 1 - Verify only relevant changes (Priority: P1)

Maintainers receive fast automatic verification for non-product changes and bounded
verification for test-only changes, without losing explicit full acceptance.

**Independent Test**: Disposable repositories and command spies establish route and
selection behavior without adding tests of project tooling to the product suite.

**Acceptance Scenarios**:

1. Given documentation, instructions, tools, dependencies or infrastructure changes,
   automatic verification performs hygiene, applicable native documentation analysis,
   static checks and commit safeguards without product tests or live infrastructure.
2. Given test-only changes, verification executes changed eligible unit files and valid
   failed IDs, plus known dependents of shared fixtures/helpers. Live and heavy scenarios
   are excluded; stale IDs are discarded; missing dependency history is an explicit gap.
3. Given product source or shipped runtime configuration/assets under `src/`, ordinary
   product verification runs. Prose remains non-code; mixed changes use the strongest route.
4. Given an earlier product commit and a documentation follow-up, the automatic post-commit
   run considers the latest commit only. Hooks consider the staged diff, including both
   sides of renames and deletions. Explicit tests/acceptance/release retain requested scope.
5. Given early failure or automatic edits, expensive execution does not start. An empty
   test selection launches no pytest process; bounded selection cannot expand to a suite.

### User Story 2 - Maintain supported coverage with less machinery (Priority: P2)

Maintainers have one verification policy and concise decision-oriented skills.

**Independent Test**: Compare retained contracts and collection against the original tree.

**Acceptance Scenarios**:

1. Hygiene covers tracked eligible files, preserves automatic whitespace/newline fixes,
   exclusions and the 512 KB limit; edits fail for inspection. Ruff fixes stay explicit.
2. One staging check runs before the hook dispatcher can stash. Conventional Commits,
   worktree awareness, declarative import boundaries, runtime import and target behavior,
   mutation selection and process cleanup remain enforced.
3. Custom static effect checks and tooling/packaging/metadata/infrastructure-only tests
   are removed. Purity guidance and the reduced automated coverage remain explicit.
4. Physical multi-GPU-only tests and exclusive configuration disappear. External multi-user,
   two-host NFS, physical multi-GPU and unavailable ClearML UI are no longer mandatory gates.
   Product capabilities and CPU DDP, simulations, single-GPU direct/queued execution,
   publication/readback, FiftyOne, chart rendering and paired integration remain supported.
5. Six maintained skill names remain; historical evidence and installed Spec Kit files
   are preserved. Acceptance claims link to contracts and concrete verification.

### User Story 3 - Safely automate explicit release operations (Priority: P3)

Maintainers can integrate/version locally independently of permission to publish.

**Independent Test**: Disposable release repositories and controlled commands exercise
refusal paths without a real release or push.

**Acceptance Scenarios**:

1. Explicit local release checks clean expected commits under a nonblocking shared lock,
   integrates by fast-forward only, and lets semantic-release own versions/changelog/tags.
2. Final proposed CY and queue versions pass paired verification once before commit/tag.
   No-version outcomes check the unchanged pair once. Failure leaves prepared changes
   for explicit recovery and creates no release commit/tag.
3. Immediate authorized publishing reuses that invocation's gates; later publishing runs
   a fresh pass without re-versioning, pushes only intended refs and confirms them remotely.
4. Dirty trees, moved refs and held locks refuse completion. No persistent receipt system
   is introduced; unavailable supported verification remains deferred and blocks delivery.

### Edge Cases

Missing/corrupt dependency history, deleted tests, renamed files, parameterized stale IDs,
all-heavy or empty selections, no parent commit, partial staging, concurrent ref movement,
interrupted cleanup, no-version outcomes and validation failures are explicit cases.

## Requirements

### Functional Requirements

- **FR-001**: Automatic checks MUST implement all US1 routes using one classifier.
- **FR-002**: Early checks and fixes MUST precede expensive stages; successful evidence
  MUST remain reusable while relevant inputs are unchanged. Final automatic verification
  MUST use the complete hook pass with overrides cleared, without an equivalent prior run.
- **FR-003**: Consolidation MUST preserve US2 safeguards and supported product behavior,
  explicitly record removed coverage and add no separate documentation checker.
- **FR-004**: Release entrypoints MUST implement US3 authorization and refusal behavior.
- **FR-005**: Verification MUST use disposable tooling scenarios, retained product collection,
  applicable explicit acceptance and fresh independent review; report actual gaps.

### Key Entities

- Change set: staged or latest-commit paths, including original and destination names.
- Bounded selection: current eligible test IDs/files plus recorded dependency evidence/gaps.
- Release attempt: expected commits, held lock, final version pair and intended refs.

## Success Criteria

- **SC-001**: Every non-product scenario launches zero product test/live processes.
- **SC-002**: Test-only executions remain within the stated selection in every scenario.
- **SC-003**: Every tested early/release refusal stops before prohibited expensive work or tagging.
- **SC-004**: Removed code/coverage and retained collection are measured in dated evidence;
  no product capability, dependency pin or unrelated work changes.

## Assumptions

The supplied plan authorizes implementation and local task commits, but no real release
or publishing. Existing supported live gates may be deferred only with reported evidence.
Project native Spec Kit owns artifacts; the implementation does not alter installed tooling.

## Approved architecture reduction

Remove custom architecture scanners without adding tools or moving source scanners into
product tests. Fixed-name dynamic imports become ordinary local imports at the same
execution point; computed DEIM loading remains a narrow exception. Ruff and import-linter
own explicit dependency restrictions. Product tests exercise initializer behavior,
configuration targets, console metadata, worker destinations, plugin registration and
resources. No public runtime interface or supported behavior changes.

Retire global cycle prohibition, initializer call/decorator syntax bans, blanket core
and pure-helper dependency allowlists, packager member/external-library allowlists,
and scanning of all dotted source strings. Preserve explicit layers, SDK ownership,
adapter and queue boundaries, product/test separation and packager module restrictions.
Tests establish exercised behavior, not every possible import order or unexecuted branch.
No new tool, release, push, upstream revision change or installed Spec Kit edit is authorized.
