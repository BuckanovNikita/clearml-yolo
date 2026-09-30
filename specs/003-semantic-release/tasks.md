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

## Phase 7: Changelog amendment (2026-09-30)

- [x] T014 Add failing real Git/hook changelog scenarios to tests/test_local_release.py.
- [x] T015 Configure full-history Markdown generation in pyproject.toml and an always-running pre-commit hook in .pre-commit-config.yaml; depends on T014.
- [x] T016 Extend scripts/local_release.py with refresh, release inclusion, checksum validation and protected recovery; depends on T015.
- [x] T017 Run the complete release acceptance suite and required quality gates; depends on T016.

## Phase 8: Documentation update

- [x] T018 Reconcile README.md, specs/003-semantic-release/{spec.md,plan.md,data-model.md,research.md,contracts/local-release.md,quickstart.md}, and docs/current-contracts.md with the implemented changelog behavior; depends on T016.
- [x] T019 Validate changed Markdown structure, local links and release-command examples; record results and limits in docs/evidence/2026-09-30-changelog-release.md; depends on T017 and T018.
- [x] T020 Review all authorized workspace changes for publication; depends on T019.

The user explicitly requests committing the reviewed snapshot, creating the checked
next release and pushing master plus its exact annotated tag after these gates. Final
commit/tag and remote-ref evidence is reported in the publication session; fixture tests
remain isolated and do not publish.
