# Workspace cache and instruction review

**Date**: 2026-10-02.
**Scope**: the approved workspace-cache-boundary correction and the existing instruction
extraction, reviewed together before the requested commit and push.

## Fresh verification

- `uv run --locked --no-sync pytest -q`: 721 passed, 8 skipped, 4 upstream
  Hydra/Pydantic deprecation warnings. The skipped FiftyOne publication tests require
  an explicitly selected isolated database and opt-in environment.
- Ruff: passed. Strict mypy: passed for 96 source files. Import-linter: 9 contracts kept.
- Parsed 23 changed/new Markdown files, validated 106 local links/anchors, and passed
  `bash -n` for 19 shell examples. The relative `CLAUDE.md -> AGENTS.md` symlink is intact.
- Parent inspected the complete application diff. Fresh instruction reviewer
  `/root/guidance_review` returned **ship**, no findings: extracted product/workflow
  requirements, pinning and commit safeguards are retained.
- The source reviewer found two missed current XDG-default statements in the CLI contract
  and feature 008 FR-004. Both were corrected to the XDG-independent null dataset-cache
  default; a fresh reviewer checks the correction before final acceptance.
- The first checkout hook attempt saw unrelated publication edits arrive during execution.
  It reported an unreachable statement in a newly added publication test; a cold mypy check
  and the exact mypy hook subsequently passed. Pytest passed 735 tests with 9 skips but the
  hook rejected concurrent file changes. This was not a passing all-hooks run.
  Commit checks therefore use an isolated worktree containing only the reviewed changes.

## Commit safeguards

Only reviewed paths are staged. The entire local `[tool.uv.sources]` section is removed
before checks/commit hooks and restored exactly, unstaged, afterward, including failures.
Hook subprocesses use the installed environment without syncing or resolving dependencies.
The normal automatic local-release hook remains enabled; version-only lockfile changes must
preserve every dependency/source record and the pinned submodule revisions.

## Isolated acceptance checks

All configured pre-commit hooks passed in a stable isolated checkout containing only the
34 reviewed paths: large-file/conflict/TOML/YAML checks, whitespace/final-newline checks,
committed-history changelog generation, Ruff, mypy, import contracts and the full pytest suite.
Imports were checked to resolve to the isolated source tree; the installed dependency
environment was reused without synchronization. The checkout contains no local uv sources
table, no unrelated publication edits and no dependency or submodule changes.

Parsed 26 staged Markdown files, checked 110 local links/anchors, and passed 19 shell examples
with `bash -n` before appending this acceptance note. Staged `git diff --check` passed.
The automatic release hook's read-only offline lock check cannot resolve the editable local
dependencies without the removed local source table. If release preparation encounters this
condition, documented recovery preserves every dependency/source record and changes only
the root project version in the lockfile; ordinary quality hooks remain enabled.

## Limits

No real GPU training or remote ClearML uploads were rerun. The existing repository-wide
broken constitution link documented in the instruction-cleanup evidence is outside this
reviewed change and remains unchanged. General dependency caches retain their defaults;
existing workspace cache contents are not migrated or deleted. Remote URLs were not fetched
for documentation validation. Commit/push identifiers are reported after publication rather
than predicted here.

## Final independent acceptance

The final independent reviewer returned `ship` with no findings. Focused boundary
verification passed (9 tests, 26 deselected), the staged diff check passed, and the
reviewer confirmed all 34 staged paths were unchanged. Native GPU execution and remote
publication were outside this review.
