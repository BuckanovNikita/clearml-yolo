# Local semantic release verification — 2026-09-28

## Scope

Implemented the approved [Spec Kit feature](../../specs/003-semantic-release/spec.md):
local Python Semantic Release version calculation, checked metadata commits, annotated
tags, pre-1.0 policy, hook installation, and recovery. No application entrypoints changed.
No repository implementation commit, release tag, push, distribution build, or publication
was performed for acceptance. Temporary fixture repositories created their own test commits
and tags. Dependency installation used uv's ordinary editable project installation.

## Checks

- Baseline: `uv run --locked pytest -q` passed 343 tests with three upstream
  hydra-zen/Pydantic deprecation warnings.
- The initial release acceptance test failed because the hook had no implementation.
  The implemented transaction passed the initial 16 cases, then the expanded 31 cases.
- Full `uv run --locked pytest -q` passed 374 tests with the same three warnings.
  An additional unreachable-tag-conflict regression passed independently afterward.
- Final collection contained 375 tests, including 32 local-release cases.
  `uv run pre-commit run --all-files` passed all ten existing check hooks, including
  the full pytest suite, against that final test set.
- Ruff passed; strict mypy passed for 65 source files; all seven import contracts passed.
- `pre-commit validate-config` passed. Generic file hooks also checked new, still-untracked
  source/specification files explicitly; no applicable checks failed.
- Markdown fences, placeholders, local links and Git whitespace checks were validated.

## Acceptance evidence

Real temporary repositories exercised installed pre/post-commit hooks, PSR 10.7.0,
offline uv lock refresh, ordinary checked commits, and annotated tags. Cases cover
fix/perf, feature, both breaking-change conventions, non-release commits, previously
unreleased history, detached HEAD, feature branches, rewrite state, actual amend and
single cherry-pick, `commit -a`, path-limited commits, dirty index/worktree, untracked
files, shallow/missing history, hook rejection, tag failures, retries, tag collisions,
stale recovery state, and locks shared across linked worktrees. Injected dependency drift
and concurrently staged work were rejected without tagging or committing unrelated files.

Three independent review findings were resolved and regression-tested:

1. Standard pre-commit post-commit execution hides dirty work via temporary stashing.
   The installed-hook regression failed before adding an owned `--all-files` launcher
   and passed afterward. Installation therefore uses `--install-hooks`; plain
   `pre-commit install` remains responsible for pre-commit checks only.
2. Amend can run after Git's operation markers disappear. The real amend regression
   failed before automatic mode inspected the reflog action and passed afterward.
3. Concurrent staging could enter an unrestricted release commit. The injected race
   failed before path-limited commits were used and passed afterward; the unrelated
   file remains staged, and dirty-tree validation prevents tagging.

No review findings remain deferred. Fixture hook checks establish Git lifecycle behavior;
the separate repository gates establish application regression status.

## Repository state and limits

Parsed lockfile comparison showed no changes to any pre-existing dependency package.
Only PSR and its additional dependencies were added; both external submodule revisions
remain unchanged. The main checkout retains its original HEAD and all original tag
references. The read-only PSR preview returned `0.4.0` for its existing unreleased history.

The installer successfully installed the project-owned post-commit launcher and existing
pre-commit checks in this checkout. Before/after comparison confirmed installation did
not create a commit or alter any tag. Existing custom post-commit hooks are protected by
an acceptance test that verifies refusal without replacement.

The feature provides local version markers only. Native training, GPU execution,
ClearML uploads, remote pushing, and publication were outside this task's scope and
were not exercised. Hard process termination can leave a lock requiring owner inspection;
handled failures retain diagnostic edits and recovery information as documented.
