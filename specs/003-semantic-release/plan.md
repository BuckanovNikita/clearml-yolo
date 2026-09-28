# Implementation Plan: Local Semantic Release

**Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

## Summary

Use a repository development script and Python Semantic Release (PSR) for automatic
local versioning. The post-commit helper computes and stamps a version, refreshes
only the project lock metadata, then uses ordinary Git to create a checked release
commit and annotated tag. No application code or public entrypoints change.

## Technical Context

- Python 3.12; existing uv, pytest, Ruff, strict mypy and pre-commit tooling.
- PSR 10.x is a development dependency, locked with the other tools.
- Local Git metadata stores a cross-worktree exclusive lock and per-worktree recovery
  record. No credentials, remote calls, changelog, distribution build or publishing.
- Tests use real Git, PSR, uv lock, and installed pre-commit hooks in temporary
  repositories; lightweight fixture check hooks replace application checks there.
- Portable Python filesystem locking uses exclusive directory creation. An interrupted
  process may leave a lock; recovery instructions require verifying its owner first.

## Constitution Check

Pre-design and post-design gates pass: no runtime boundaries or nine command contracts
change; existing quality hooks remain enabled; no dependency checkout/pin is advanced.
Only explicit version paths are staged. No stash/reset/revert or hook bypass is used.
README is Russian; other documentation and code messages are English. Machine-specific
facts are excluded. Real GPU/ClearML verification is outside local tag automation.

## Project Structure

- `scripts/local_release.py`: typed local hook/retry CLI; version calculation delegates
  to the installed PSR CLI, keeping this script outside the runtime package.
- `tests/test_local_release.py`: real temporary-repository integration and failure tests.
- `pyproject.toml`, `uv.lock`: development dependency and PSR policy.
- `.pre-commit-config.yaml`: existing hooks restricted to pre-commit; post-commit helper. A project installer launches that stage with `--all-files`
  so pre-commit does not hide dirty tracked changes before release preflight.
- `README.md`: setup and recovery; this feature directory holds specification artifacts.

## Implementation Sequence

1. Capture failing automatic-hook scenarios and configure the PSR policy.
2. Implement clean-tree preflight, local version stamping, invariant-checked lock refresh,
   ordinary checked commit, annotated tag, and recursion/concurrency protection.
3. Implement recovery and negative scenarios, retaining evidence on failure.
4. Document installation and explicit pushing; run all gates and review the diff.

## Release Transaction

- Skip recursive invocations, non-master or detached HEAD, and active history operations.
  Automatic calls also inspect the latest reflog action to skip amend/cherry-pick/rewrite
  commits whose operation markers have already been removed by Git.
- Reject shallow history before PSR can automatically fetch. Require a reachable version
  baseline. Acquire the common-directory lock before inspecting mutable release state.
- A clean tracked tree/index is mandatory before starting. Untracked files are untouched.
- Use PSR `version --print` to calculate; compare with reachable tags to distinguish a
  no-op from a conflicting existing tag elsewhere in history.
- Write recovery metadata before stamping. Run PSR with no commit/tag/build/changelog/
  push/VCS release; it may stage the declared version file even with no commit.
- Refresh `uv.lock` offline. Compare its parsed contents with the committed original,
  allowing only the root package version to change; do not upgrade dependencies.
- Stage explicit metadata paths and invoke ordinary path-limited `git commit --only` with the recursion
  guard set only for the helper. All configured pre-commit checks still run.
- Verify commit parent, changed paths and final metadata; annotate the checked commit.
- Retain the recovery record until successful tagging. A clean matching release commit
  can be rechecked and tagged on retry; dirty failed preparation requires the contributor
  to inspect/fix and commit only the two metadata files. With the installed hook, that
  manual release commit invokes tag recovery automatically; otherwise retry explicitly.
- Existing tags are never replaced. The operation lock is released on handled exits;
  a hard crash requires owner inspection and manual stale-lock removal.
