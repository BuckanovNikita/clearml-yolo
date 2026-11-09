---
status: accepted
date: 2026-11-09
---

# semantic-release with a guarded lock refresh, under flock, after two acceptance tiers

## Context

Releases used a bespoke script (`scripts/local_release.py`) that evaluated Conventional
Commits, wrote the changelog, created version commits and tags, kept a recovery record
and skipped a hard-coded list of heavy hooks. It duplicated what python-semantic-release
does and its recovery state was a second source of truth. The sibling project cveta2
releases with semantic-release, a reduced check of the version commit, an exclusive
`flock` around fast-forward integration and tagging, and clean-tip acceptance.

Adopting that model here meets one obstacle: `digital-metrics` and `report-generator`
are approved local source copies under `external/`, not packages on a reachable index.
Committed path sources in `[tool.uv.sources]` break installation from a git link: uv
rewrites them to `git+…#subdirectory=external/…` requirements that do not exist in the
repository. Keeping those sources as an uncommitted override instead meant the committed
project alone could not be locked, every Task stage had to run without lock checks and
the staging guard needed an exemption for the override.

## Decision

- The committed `pyproject.toml` declares both packages by version only and never
  contains `[tool.uv.sources]`. A gitignored repository-root `uv.toml` sets
  `find-links = ["external/wheelhouse"]`; source distributions of the approved copies are
  built into that ignored directory, and `uv.lock` records both packages as
  `source = { registry = "external/wheelhouse" }`. End users installing from a git link
  ignore the lockfile and resolve both packages from their own index.
- With no local overrides, Task stages run as `uv run --locked task --exit-code <stage>`,
  `check` runs `uv lock --check` directly and the staging guard refuses every unstaged
  tracked change and untracked file without exemption.
- semantic-release alone determines versions, the changelog and annotated `v{version}`
  tags. Its build command runs `uv lock --upgrade-package clearml-yolo` to refresh the
  root version entry. With `CY_RELEASE_CHECK=1` it runs `release-commit-check`: only
  `pyproject.toml`, `uv.lock` and `CHANGELOG.md` may be staged, the staged project may
  differ from `HEAD` only in its version and declares no sources, and the lockfile's
  packages must equal `HEAD` except the `clearml-yolo` version
  (`scripts/release_lock_guard.py`); lock freshness, read-only Ruff and deptry run
  again. That version commit alone may use `SKIP=verify`.
- Fast-forwarding `master` to the accepted tip, versioning, tagging and the authorized
  push happen under `flock -n <git-common-dir>/clearml-yolo-release.lock`. A held lock
  is a reported blocker. Pushing needs separate authorization.
- Verification has two acceptance tiers. Change acceptance (`acceptance`) gates
  integration: a clean tip, static checks, property exploration, a stand preflight, the
  complete unit suite with a coverage floor and a CPU smoke run on the shared ClearML
  stand; documentation-only changes skip the live part. Release acceptance
  (`release-acceptance`) gates delivery: change acceptance plus the Severstal single-GPU
  suite, multi-GPU DDP when configured (otherwise waived), FiftyOne tests in a temporary
  database, the paired CY and cy-queue check in a temporary environment and, as a skill
  step, the real-run gate on CPU and a single GPU.

## Considered options

- **Keep the bespoke script.** Rejected: it reimplemented semantic-release, carried its
  own recovery record and diverged from the sibling project's maintained model.
- **Patch the root version in `uv.lock` byte-exactly without resolution.** Superseded:
  it existed only because the committed project could not lock without the uncommitted
  override. The local wheelhouse removes that override, so the standard
  `uv lock --upgrade-package` refresh, bounded by the lock guard, replaces the patch.
- **Keep an uncommitted `[tool.uv.sources]` override.** Rejected: it forced unchecked
  `--frozen --no-sync` runs, a staging-guard exemption and lock checks against a
  synthesized copy of the index.
- **Commit path sources.** Rejected: they break installation from a git link.
- **Commit pinned git sources.** Rejected: end users have no GitHub access.
- **Declare the sources in `uv.toml`.** Not possible: `uv.toml` rejects `sources` and
  ignores `override-dependencies` for project locking; it can only add `find-links`.
- **One acceptance tier.** Rejected: GPU and paired checks need the user's GPU and a
  sibling checkout, which would block every integration; without them delivery would
  be unverified.

## Consequences

Each worktree needs its own `external/` copies (or a symlink), the built wheelhouse and
`uv.toml` before syncing; the Task stage `local-deps` prepares the last two. External
packages are no longer installed editable, so a change of an approved copy needs a
wheelhouse rebuild, which the digital-metrics pin rule already restricts to explicit
user intent. The release runs the resolver for the root package, and the lock guard
fails the release on any other lockfile change, which must land as an ordinary reviewed
commit first. A failed attempt can leave staged version files; recovery restores only
that attempt's changes and re-accepts the fixed tip, never hand-editing versions or tags.
Releases need a clean prepared checkout in which `master` can be checked out, which may
require a dedicated release worktree. Release acceptance can be deferred while the GPU
serves the user's workload; multi-GPU DDP on a single-GPU host is waived, not deferred.
Model-weight releases and the ban on building distributions for releases are unchanged;
the local source distributions are development inputs, never release deliverables.
