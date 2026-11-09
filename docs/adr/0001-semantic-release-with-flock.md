---
status: accepted
date: 2026-11-09
---

# semantic-release with a byte-exact root lock patch, under flock, after two acceptance tiers

## Context

Releases used a bespoke script (`scripts/local_release.py`) that evaluated Conventional
Commits, wrote the changelog, created version commits and tags, kept a recovery record
and skipped a hard-coded list of heavy hooks. It duplicated what python-semantic-release
does and its recovery state was a second source of truth. The sibling project cveta2
releases with semantic-release, a reduced check of the version commit, an exclusive
`flock` around fast-forward integration and tagging, and clean-tip acceptance.

Adopting that model here meets one obstacle: `digital-metrics` and `report-generator`
are editable copies under `external/` that the committed `pyproject.toml` names by
version only, with the path sources kept as an uncommitted `[tool.uv.sources]` override.
The committed project alone cannot be locked, so refreshing the version entry with
`uv lock` inside the release would need the override, could re-resolve dependencies and
could move the pinned `digital-metrics` entry.

## Decision

- semantic-release alone determines versions, the changelog and annotated `v{version}`
  tags. Its build command patches only the root `clearml-yolo` version in `uv.lock`,
  byte-exactly and without dependency resolution (`scripts/release_version.py`). With
  `CY_RELEASE_CHECK=1` it runs `release-commit-check`: only `pyproject.toml`, `uv.lock`
  and `CHANGELOG.md` may be staged, the lockfile may differ from `HEAD` only in that
  root version (`scripts/release_lock_guard.py`), and lock freshness, read-only Ruff
  and deptry run again. That version commit alone may use `SKIP=verify`.
- Fast-forwarding `master` to the accepted tip, versioning, tagging and the authorized
  push happen under `flock -n <git-common-dir>/clearml-yolo-release.lock`. A held lock
  is a reported blocker. Pushing needs separate authorization.
- Verification has two acceptance tiers. Change acceptance (`acceptance`) gates
  integration: a clean tip, static checks, property exploration, the complete unit suite
  with a coverage floor and a CPU smoke run on the shared ClearML stand; documentation-only
  changes skip the live part. Release acceptance (`release-acceptance`) gates delivery:
  change acceptance plus GPU-marked tests, FiftyOne tests, the paired CY and cy-queue
  check and, as a skill step, the real-run gate on CPU and a single GPU.
- The staging guard keeps a narrow exemption for the uncommitted source override:
  `pyproject.toml` differing from the index only inside `[tool.uv.sources]`, optionally
  with `uv.lock`. Lock freshness checks staged content with the canonical sources added,
  so the override never masks drift. Releases run from a clean checkout without it.

## Considered options

- **Keep the bespoke script.** Rejected: it reimplemented semantic-release, carried its
  own recovery record and diverged from the sibling project's maintained model.
- **`uv lock --upgrade-package clearml-yolo` inside the build command.** Rejected: it
  needs the override and a resolver run during the release, and can change other lock
  entries, including the pinned `digital-metrics`.
- **Commit the source override.** Rejected: the committed project would depend on local
  `external/` paths for every consumer instead of only for development.
- **One acceptance tier.** Rejected: GPU and paired checks need the user's GPU and a
  sibling checkout, which would block every integration; without them delivery would
  be unverified.

## Consequences

The release tool no longer resolves dependencies, so any `uv.lock` change other than the
root version fails the release and must land as an ordinary reviewed commit first. A
failed attempt can leave staged version files; recovery restores only that attempt's
changes and re-accepts the fixed tip, never hand-editing versions or tags. Releases
need a clean checkout without overrides in which `master` can be checked out, which may
require a dedicated release worktree. Release acceptance can be deferred while the GPU serves the
user's workload; multi-GPU DDP on a single-GPU host is waived, not deferred. Model-weight
releases and the ban on building distributions for releases are unchanged.
