---
name: release
description: Integrate an accepted clearml-yolo tip into master by fast-forward and evaluate semantic-release under the shared release lock. Use for code releases, blocked acceptance before release, release-commit-check failures, a held release lock, or recovery of staged version, changelog or lockfile changes.
---

# Merge and release clearml-yolo

[Local releases](../../../docs/development.md#local-releases) own policy. semantic-release
alone owns versions, changelog and `v{version}` tags. Publish Git version tags only: no
GitHub Releases, wheels or source archives for code. Model-weight releases follow
[their own procedure](../../../docs/development.md#model-weight-releases) unchanged.
`BRANCH` below names the branch to land; push authorization is separate.

## 1. Accept the clean branch tip

Work from a clean prepared checkout of `BRANCH` with its own `.venv`, `external/`
copies, built wheelhouse and `uv.toml`
([setup](../../../docs/development.md#external-dependencies)). Inspect host load, choose
`CY_TEST_WORKERS` and, with `SKIP` cleared:

```bash
git fetch origin
git rebase origin/master                                  # only when needed
uv run --locked task --exit-code acceptance
uv run --locked task --exit-code mutation -- --base master   # code changes
uv run --locked task --exit-code release-acceptance          # before delivery
```

Code changes also need fresh independent review after integration and verification.
`release-acceptance` includes the paired release check (`CY_QUEUE_DIR`, default
`../cy-queue`, run in a temporary environment); also run the real-run gate of
`running-end-to-end-tests` on CPU and a single GPU. Use `running-integration-tests` for
the live part: UNAVAILABLE/3 or a GPU busy with the user's workload (check pcboard
`pc_status` first) is deferred verification, ERROR/1 needs diagnosis. Multi-GPU DDP is
waived unless `CY_DDP_ARGS` is set and does not block; the Severstal single-GPU suite
(`CY_SEVERSTAL_ARGS`) is required. Every other required check must pass. Record the accepted tip and outcomes; a changed tip needs fresh
acceptance.

## 2. Merge, release and push under the lock

Proceed only with separate authorization to push `master` and the release tag;
otherwise stop after reporting acceptance. Set `ACCEPTED_TIP` to the commit just
accepted; never infer acceptance from a branch name or an old run.

```bash
git switch master
flock -n "$(git rev-parse --git-common-dir)/clearml-yolo-release.lock" bash -c '
  set -e
  test "$(git rev-parse "$1")" = "$2"
  test -z "$(git status --porcelain)"
  git fetch origin
  git merge --ff-only origin/master
  git merge --ff-only "$1"
  test "$(git rev-parse HEAD)" = "$2"
  uv run --locked semantic-release version --print
  CY_RELEASE_CHECK=1 SKIP=verify uv run --locked semantic-release version --no-push --no-vcs-release
  git push origin master --follow-tags
' _ "$BRANCH" "$ACCEPTED_TIP"
git ls-remote origin refs/heads/master 'refs/tags/v*'
```

The lock covers fast-forward through push. Report these as blockers rather than working
around them:

- `flock` fails: another release holds the lock; never wait on or break it.
- `git switch master` fails because `master` is checked out in another worktree, or the
  clean-tree test fails.
- A fast-forward fails or the tip moved: return to step 1; never tag a different tip.

No releasable commits means no version: a successful outcome that pushes only `master`
when authorized.

semantic-release's build command runs `uv lock --upgrade-package clearml-yolo` to refresh
the root version entry in `uv.lock`; with `CY_RELEASE_CHECK=1` it then runs
`release-commit-check` before committing. The check permits only staged
`pyproject.toml`, `uv.lock` and `CHANGELOG.md` with no unstaged or untracked inputs,
requires the staged project to differ from `HEAD` only in its version and to declare no
`[tool.uv.sources]`, requires every lock package except the `clearml-yolo` version to
equal `HEAD` (`scripts/release_lock_guard.py`), and reruns lock freshness, read-only Ruff
and deptry. Any other lock change lands first as an ordinary reviewed commit.
`SKIP=verify` is the documented exception for this version commit only; message
validation and the staging guard stay active.

## Failed release recovery

A failed build command or check may leave this attempt's version, changelog and lockfile
changes staged without a commit or tag. Inspect `git status`, the staged diff and actual
tags; establish which changes this attempt created. Restore only those, fix the cause on
the branch and accept the new tip again. Never hand-edit a
version or tag, widen the exception, discard unrelated work or claim a partial release
passed.

## Report

Report the accepted and merged tips, required check outcomes (passed, failed, deferred,
waived), mutation findings, the paired check's SHAs and versions, the version or
no-release decision, and the actual release commit and tag. Confirm pushed refs remotely.
