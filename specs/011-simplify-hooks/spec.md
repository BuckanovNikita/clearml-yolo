# Feature Specification: Plain prek hooks with cached pytest

**Created**: 2026-11-06
**Status**: Implemented and independently reviewed; see [verification](verification.md).
**Baseline**: [Stage zero](../000-baseline/spec.md); supersedes the receipt-reuse
verifier introduced by [005](../005-reduce-verification/spec.md).

## Intent and boundaries

`scripts/verify.py` wraps five ordinary checks: Ruff, mypy, Vulture, import-linter and
the full pytest suite. `--docs` runs the documentation checker. Most of its code fingerprints
inputs and stores Git-private receipts. That cache exists only so the roughly
16.5-minute suite does not run again on the automatic `chore(release)` commit or
during tag recovery. The cache has proven fragile: on 2026-11-06 it refused to record a pass
because file stat identity drifted, and the commit needed an approved hook skip
([evidence](../../docs/plans/unfinished-work-cleanup-20261106/verification.md)).

The user chose to:

- remove `verify.py` and run plain hooks through **prek**;
- keep pytest in the pre-commit stage, reusing caches where possible;
- keep the `changelog` hook;
- stop heavy hooks from running again on the generated release commit.

There is no change to application behaviour, CLI, configuration or runtime packages.

## User scenarios and acceptance

### US1: Contributors commit with ordinary, cached hooks (P1)

Acceptance:

- A commit that touches Python runs Ruff, mypy, Vulture and import-linter, plus pytest
  limited by testmon to the tests affected by the change.
- A commit that touches governed non-Python inputs runs the full suite.
- A documentation-only commit runs only hygiene and documentation checks.
- After a full acceptance run, a commit of unchanged code selects no tests.

### US2: Releases do not repeat heavy checks (P1)

Acceptance:

- The generated `chore(release)` commit and the tag-recovery hook run skip the heavy
  hook IDs. Hygiene and changelog hooks still run.
- The existing byte-exact metadata validation remains the guard for these commits.
- A failing quality hook on the contributor commit still leaves the commit in place
  without a release tag.

### US3: One simple canonical procedure (P1)

Acceptance:

- Current guidance names the direct commands, the `prek` runner and the full acceptance
  command `pytest --testmon-noselect`.
- `scripts/verify.py`, its tests and its import allowances are removed.
- `local_release.py` owns its version-token rewrite.

## Requirements

- FR-001: Replace `pre-commit` with `prek` in the dev group. Change the lockfile only by
  that swap and by adding `pytest-testmon`. The external dependency entries must stay
  byte-identical.
- FR-002: Hook configuration uses only the project's locked tools through
  `uv run --frozen --no-sync`. Whole-repository checks do not take filename lists.
- FR-003: The full suite remains the required acceptance before commit or release. The
  hook is a fast gate: testmon does not track code that runs only in subprocesses, or
  environment changes that leave files unchanged.
- FR-004: The release helper sets `SKIP` for heavy hook IDs only on its own generated
  commit and during tag recovery.
- FR-005: Move `version_bytes` into `scripts/local_release.py` unchanged in behaviour,
  and keep its tests.
- FR-006: Update current guidance. Completed feature and bug evidence remains unchanged.
