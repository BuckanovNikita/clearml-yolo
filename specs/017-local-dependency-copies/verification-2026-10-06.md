# Verification — 2026-10-06

## Dependency conversion

Both original dependency worktrees were clean at the approved revisions recorded
in the development guide. Before/after SHA-256 manifests matched all 12,184 files
in digital-metrics and 58 files in report-generator, excluding .git pointers and
Python bytecode caches. Untracked source-tree files were preserved too. The obsolete
pointer files and original Git object databases remain in ignored parent Git metadata
for recovery. No dependency source was edited and no dependency revision changed.

The Git index contains no mode-160000 entries; git submodule status is empty.
Both local dependency paths match the new ignore rules. Frozen dev sync succeeded,
and both package imports resolve to the existing local source trees. cy --help
succeeded. TOML parsing, changed Markdown structure, local link targets and diff
whitespace checks passed. README remains usage-only, as established by its active
specification; historical release notes and completed task history were preserved.

## Release preparation

The first full hook invocation regenerated CHANGELOG.md, then plain uv run attempted
registry resolution without local source overrides and failed to find digital-metrics.
That attempt was stopped; source overrides were restored. The full hooks were rerun
with UV_NO_SYNC=1 against the existing environment, following the previous release's
method. No hooks are skipped. Final results are recorded below when available.

A real offline lock refresh in a disposable project with the saved local overrides
confirmed that release 0.17.1 changes only the root package version. A temporary
process adapter supplies that validated lock refresh to the unchanged release helper;
all other uv commands pass through. Local overrides stay absent during commit/release
hooks and are restored afterward. The adapter will be removed after the release.

This repository-metadata change does not claim new native training, GPU, ClearML or
FiftyOne acceptance. GitHub SSH and HTTPS connections timed out during preparation;
remote publication remains unverified until a push succeeds.

## Pre-commit validation results

The full pytest suite completed: 1,161 passed, 29 skipped, 12 warnings in 293.15s.
Ruff, mypy (133 files), all nine import contracts and the other validation hooks
passed. The pytest hook reported files modified because the parent corrected
quickstart documentation while that hook was running; no test failed. The commit
will rerun normal hooks with a stable diff. Changed Markdown links and anchors were
validated again after that correction. Fresh independent review returned ship,
subject to successful commit hooks and truthful reporting of the blocked push.

## Release and publication result

- Change commit: `5b49ec9`; release commit: `136503a`.
- Both normal commit and release hooks passed, including the full pytest suite.
- Annotated v0.17.1 resolves to the release commit. Its diff contains only version
  metadata, the root lockfile version and the generated changelog; dependency
  resolution is unchanged.
- The first successful atomic SSH push created remote main and v0.17.1. Remote
  ref readback confirmed main and the peeled tag at the release commit.
- Local source overrides were restored unstaged. No release lock or recovery record
  remains. The temporary release adapter and task-owned help output were removed.
- Publication contains Git commits and a version tag only; no package assets were
  uploaded. Remote default-branch settings and the master release policy are unchanged.
