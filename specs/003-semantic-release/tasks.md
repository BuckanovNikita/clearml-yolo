# Tasks: Local Semantic Release

**Input**: [spec.md](spec.md), [plan.md](plan.md), research, data model and contract.

## Phase 1: Setup

- [x] T001 Create specification, checklist and design artifacts in specs/003-semantic-release/.
- [x] T002 Add and lock the PSR development dependency in pyproject.toml and uv.lock without advancing existing dependencies.

## Phase 2: Foundation

- [x] T003 Configure PSR version policy in pyproject.toml and explicit hook stages in .pre-commit-config.yaml; install the post-commit launcher with --all-files.
- [x] T004 Create real temporary-repository fixtures in tests/test_local_release.py and observe missing-hook failures.

## Phase 3: US1 - Automatic local versioning

**Independent test**: real fixture commits produce the expected metadata commit and tag.

- [x] T005 [US1] Test fix/perf, feature/breaking, non-release history and idempotence in tests/test_local_release.py.
- [x] T006 [US1] Implement PSR calculation/stamping, checked metadata commit and annotated tag in scripts/local_release.py.

## Phase 4: US2 - Preserve contributor work

**Independent test**: negative cases preserve original commits, files and tags.

- [x] T007 [US2] Test dirty index/worktree, branches, shallow history, rewrite state, dependency drift and rejected checks in tests/test_local_release.py.
- [x] T008 [US2] Implement preflight, immutable-dependency verification, recursion guard and exclusive common-directory lock in scripts/local_release.py.

## Phase 5: US3 - Recover a local release

**Independent test**: fail after the metadata commit, retry and obtain only its missing tag.

- [x] T009 [US3] Test tag failures, collisions, concurrent attempts and stale recovery state in tests/test_local_release.py.
- [x] T010 [US3] Implement attempt ownership, revalidation and idempotent retries in scripts/local_release.py.

## Phase 6: Polish and verification

- [x] T011 Document contributor installation, categories, recovery and explicit pushing in README.md.
- [x] T012 Run all gates, document checks in docs/evidence/2026-09-28-semantic-release.md, and complete specs/003-semantic-release/analysis.md.
- [x] T013 Review the integrated diff, install validated hooks locally, and verify installation creates no release.

## Dependencies and strategy

T001–T004 precede US1; US2/US3 extend the same transaction and are implemented sequentially.
Documentation can be reviewed independently while tests run. No parallel writers share
the helper or test file. Deliver the basic transaction, then preservation/recovery, then
full verification. The main repository is not committed, tagged or pushed for testing.
