# Development procedures

This document owns every development command and procedure, for contributors and agents.
Always-apply policy lives in [AGENTS.md](../AGENTS.md), code-structure rules in
[architecture](architecture.md), and product behavior in the [feature files](feature/).

## Verification

[Taskfile.yml](../Taskfile.yml) owns verification commands, order and change routing;
[Taskfile.ops.yml](../Taskfile.ops.yml) owns bootstrap, infrastructure, acceptance and
pairing. prek ([.pre-commit-config.yaml](../.pre-commit-config.yaml)) dispatches Task
serially and validates Conventional Commit messages. Prepare the
[external dependencies](#external-dependencies), clear any inherited
`UV_PROJECT_ENVIRONMENT`, then run `uv run --locked task --exit-code <stage>`.

Task pins every tool to this worktree's `.venv` and caches and keeps no freshness cache;
neither a skipped nor an interrupted run is evidence. `CY_TEST_WORKERS` (default `2`) sets
the xdist worker count; check host load before heavy stages.

### Automatic routing

`verify` runs `check`, then `scripts/verification.py` classifies one change set. Its scope
is `CY_VERIFY_SCOPE` (`auto`, `staged`, `working`, `commit`; the pre-commit hook sets
`staged`). `auto` takes the staged diff, else uncommitted changes, else the latest commit.

| Changed inputs | Route |
| --- | --- |
| Prose (`.md`, `.rst`, `.txt`, `.adoc`), tooling, dependencies, infrastructure | Static: `check` only |
| Test code only | Bounded test selection |
| Any non-prose file under `src/` | Product: `task test` (testmon-affected unit tests) |
| Mixed | The strongest applicable route |

- Renames and deletions count the old and the new path. `tests/integration/lifecycle.py`
  and `tests/integration/environment/` are infrastructure.
- A prose-only commit after product commits reruns no product tests; the static route
  does not rerun cached failures.
- The bounded selection runs changed eligible `tests/**/test_*.py` files, cached failed IDs
  still in the current collection, and the testmon-recorded dependents of changed test
  files and helpers. It excludes `tests/integration` and the `ddp_cpu`,
  `process_capabilities`, `gpu_controls` and `severstal_gpu` markers. An empty selection
  starts no pytest process.
- A changed helper, or a changed test module other tests import, without recorded
  dependents prints `TARGETED VERIFICATION GAP` and exits 3; it never widens to the full
  suite.
- Explicit stages always run their whole scope.

### Order and evidence reuse

Check affected documentation against the Linear acceptance criteria as soon as the inputs
exist. Then run hygiene and safe fixes, syntax and required-input checks, lock freshness,
the remaining static checks and a resource preflight before any expensive stage. An early
failure or automatic edit stops the run; inspect and stage the edit before retrying. Reuse
a successful check while its relevant inputs and environment are unchanged: a prose
correction keeps product evidence, a review fix reruns the affected checks. The final pass
is the [commit procedure](#commit-procedure) command, with no equivalent `verify` first.

| Stage | Purpose |
| --- | --- |
| `local-deps` | Build the external wheelhouse and create `uv.toml` |
| `fix` | Safe Ruff fixes and formatting; never stages |
| `check` | `hygiene`, `lock`, `ruff`, `format-check`, `architecture`, `mypy`, `vulture`, `deptry` |
| `architecture` | import-linter contracts in [.importlinter](../.importlinter) |
| `verify` | `check` plus [automatic routing](#automatic-routing) |
| `test` / `test-full` | Affected / full unit suite; `test-full` refreshes testmon history |
| `coverage` | Full unit suite with branch coverage and the configured floor |
| `mutation` | [Mutation report](#mutation-report) |
| `infra-check` | Read-only bounded preflight of the test cluster |
| `infra-up` / `infra-env` / `infra-down` | Create, export, delete the owned test environment |
| `integration` | Owned environment, non-GPU live tests, teardown |
| `acceptance` / `release-validation` / `release-acceptance` | [Acceptance tiers](#acceptance-tiers); `release-validation` is `release-acceptance` without `paired-check` |
| `paired-check` | [Paired CY and queue check](#paired-cy-and-queue-check) |

Verification never builds CY distributions. `test`, also when the product route runs it,
may run a full baseline for an unseen testmon environment; the test-only route never
does. A deselected test is not fresh execution. For an advisory unused-code inventory
below the Vulture gate, run `uv run --frozen --no-sync vulture --min-confidence 60`.

### Lock freshness

`lock` runs `uv lock --check` and never rewrites `uv.lock`. The external packages resolve
through the ignored `uv.toml` and `external/wheelhouse`; prepare them before verifying.
Repair setup failures locally, never by changing approved revisions or committed sources
(see [AGENTS.md](../AGENTS.md)).

### Hooks and staging guard

Install the hooks with `bash scripts/install-hooks.sh`; linked worktrees share them, and
the dispatcher resolves the committing worktree. The installer saves the previous hooks
for rollback. Before prek can stash, the pre-commit dispatcher runs
`staging-check`, which refuses any unstaged tracked change or nonignored untracked file and
never stages, stashes or deletes anything. `hygiene` checks tracked regular text files
(not symlinks or binaries) for conflict markers and Python, TOML and YAML syntax, requires
the workflow inputs, and fixes trailing whitespace and final newlines; a fix fails the run
for inspection and staging. Added files over 512 KB fail unless Git LFS stores them. Run
`fix` before staging. Rebase, cherry-pick and merge run no hooks; verify the result
explicitly.

### Acceptance tiers

Ordinary completion runs a reviewed selection of existing stages, chosen with the
`verification-workflow` skill and recorded in the Linear issue and the PR: base and tip,
affected contracts, selected checks, exclusions, source and environment identities, reuse
reasons and gaps.

- Development covers the whole branch from its merge base; release readiness covers every
  change since the previous release, and a missing baseline requires a comprehensive
  selection. A final documentation commit does not hide earlier code.
- Localized product changes run focused tests. Shared runtime or configuration, broad
  refactors and uncertain impact run `coverage`; claim the floor only from that run.
  Product changes include a mutation report.
- Claims automated checks cannot establish (native execution, readback, rendering) need
  live or manual checks through the `running-integration-tests` skill.
- Dependency or installation changes, interfaces cy-queue consumes and uncertain
  compatibility select pairing; a version change alone does not.

`acceptance` requires a clean committed tip, runs `check`, `infra-check`, `coverage`
(including deterministic property tests) and `integration`, then proves the tip clean and
unchanged. `release-acceptance` requires `CY_SEVERSTAL_ARGS` (pytest options starting with
`--run-severstal-gpu`) and runs `acceptance` with a CUDA preflight, the single-GPU Severstal
suite, the FiftyOne suite (test-environment database, temporary lock directory), a
mutation report against
`origin/master`, and `paired-check`. Check GPU capacity before GPU stages.

Physical multi-GPU, external multi-user, two-host NFS and ClearML web-UI scenarios are
outside mandatory acceptance; never claim them from simulations or API payloads.

Report outcomes with the status vocabulary in [AGENTS.md](../AGENTS.md). Temporary
unavailability (`infra-check` or `integration` exit 3, a busy or missing GPU) defers the
check: continue independent work and retry. `infra-check` exit 1 is a configuration or
permission error to diagnose. An assertion failure after successful setup is a test failure.

### Direct test selections

```bash
uv run --frozen --no-sync pytest -m ddp_cpu
uv run --frozen --no-sync pytest -m process_capabilities
uv run --frozen --no-sync pytest tests/test_quality_properties.py tests/test_workflow_quality.py \
  --cov=clearml_yolo --cov-branch --cov-report=term-missing --cov-report=html:.tmp/coverage/html
```

Both marker suites belong to the unit suite and share the `serial` xdist group. Coverage
shows unexercised paths, not assertion quality. Reproduce an order-dependent failure with
the printed `--randomly-seed=<seed>`, or disable shuffling with `-p no:randomly`. Keep
Hypothesis's falsifying example and reproduce the failure before changing a seed or adding
a retry. Live suites run only through the `running-integration-tests` skill.

### Mutation report

`mutation` runs mutmut, through [scripts/mutation.py](../scripts/mutation.py), only on
the functions a change touches, in a throwaway workspace, and reports killed, surviving,
unreached and unjudged mutants. The script's docstring defines selection and budget;
`[tool.mutmut]` in [pyproject.toml](../pyproject.toml) holds the settings. It never runs in
a commit hook and keeps no cache. Run it for code changes before
acceptance; the `mutation-testing` skill owns survivor triage.

```bash
uv run --locked task --exit-code mutation                     # staged change
uv run --locked task --exit-code mutation -- --base master    # whole branch
uv run --locked task --exit-code mutation -- --strict         # survivors fail
```

| Exit | Meaning |
| --- | --- |
| 0 | Report produced; survivors and unreached functions are advisory |
| 1 | Under `--strict`: surviving mutants or changed functions no selected test reaches |
| 2 | Tool or configuration error, or the clean test run failed; never a pass |

## Architecture checks

Run `architecture` and the complete unit suite when changing imports, package
initializers, composition, or subprocess and plugin targets ([rules](architecture.md)).
Also verify:

- regenerated YAML examples and installed command helps, including DDP callback and
  FiftyOne extension targets, and the installed console publisher, terminal mirror and
  FiftyOne worker;
- selected-config export per command and model, project-contained destinations, and
  retained project scratch after success, failure and cancellation;
- fresh DDP callback ownership and restored in-memory settings without settings writes;
- injected subprocess hangs during import, publication and shutdown end in bounded
  warnings and validated receipts.

For interfaces shared with cy-queue, run the
[paired check](#paired-cy-and-queue-check). Use
`uv run --frozen --no-sync` for ad hoc commands in a deliberately prepared environment so
they never sync it. Task's `uv run --locked` syncs `.venv` to `uv.lock` inexactly: extra
packages such as `cy-queue` stay, locked packages return to their locked versions.

## Interpreter and dependency floors

The package supports Python `>=3.12.13,<3.14` (`requires-python` in
[pyproject.toml](../pyproject.toml)); the user-facing statement is in
[installation](feature/installation.md). `.python-version` selects the development
default, and Ruff and mypy target the oldest supported minor. When changing interpreter
compatibility, verify packaging and the routine suite on each supported minor.

[pyproject.toml](../pyproject.toml) owns lower bounds, exact pins and upper bounds;
development tools stay in `dependency-groups.dev`. When changing a floor, test an isolated
`lowest-direct` resolution on each supported minor, separate from `uv.lock`; record the
resolved versions and checks in the Linear issue and the PR; raise a floor only when
compatibility evidence requires it. Resolution alone is not a runtime check. Avoid
unrelated upgrades.

## External dependencies

`digital-metrics` and `report-generator` are ignored local source copies under `external/`,
not submodules. Copy or clone the approved revisions there; never add their contents or
Git metadata to this repository. Their pin policy is in [AGENTS.md](../AGENTS.md).

| Dependency | Upstream | Approved source revision |
| --- | --- | --- |
| digital-metrics | [repository](https://github.com/Wasilkas/digital-metrics) | `6e801be1564dce458294eb23592cc1aa0939c4d9` |
| report-generator | [repository](https://github.com/Wasilkas/report-generator) | `7339ef864b4ff1b1db499a08d647193128088e80` |

`pyproject.toml` declares both by version only; development resolves them from a local
wheelhouse of source distributions. Set up each worktree once, from its root:

```bash
uv build --sdist external/digital-metrics -o external/wheelhouse
uv build --sdist external/report-generator -o external/wheelhouse
[ -e uv.toml ] || printf 'find-links = ["external/wheelhouse"]\n' > uv.toml
uv sync --locked --dev
bash scripts/install-hooks.sh
uv run --locked cy --help
```

`local-deps` automates the first three commands; in a fresh checkout run it as
`uvx --from go-task-bin task local-deps`. It never overwrites an existing `uv.toml` and
fails if that file lacks `find-links = ["external/wheelhouse"]`; add the entry by hand.
After an authorized revision change, rerun `local-deps` and check the previous and new
interfaces the adapters use, plus application parity. Every worktree needs its own
`external/` (copy or symlink) and `uv.toml`. `uv.lock` records both packages as
`source = { registry = "external/wheelhouse" }` and does not enforce their revisions.

Why this layout:

- A committed path source in `[tool.uv.sources]` breaks installation from a git link: uv
  rewrites it to a `git+…#subdirectory=external/…` requirement that does not exist in the
  repository.
- A repository-root `uv.toml` cannot declare `sources`, but it can add `find-links`, which
  keeps all local configuration out of tracked files.
- End users install CY from a git link, ignore this lockfile and resolve both packages from
  their own package index; they have no GitHub access, so git sources are not an option.

## Commit procedure

Commit under the authorization and staging rules in [AGENTS.md](../AGENTS.md), in coherent
commits, with mechanical formatting fixes in a separate commit. Intermediate commits may
use `SKIP=verify` while final verification is outstanding; message validation and the
staging guard stay active. Never use `--no-verify` or blanket skips. Concurrent writers
use unique temporary commit-message files. After the last task
commit, run the final pass:

```bash
env -u SKIP -u PREK_SKIP -u CY_VERIFY_SCOPE -u PRE_COMMIT_ALLOW_NO_CONFIG uv run --locked prek run --all-files
```

If hooks edit files, inspect and commit those fixes separately, rerun the affected checks
and repeat the final pass until committed content passes with no outstanding edits. Never
resolve or update dependencies during verification; dependency changes land as reviewed
commits that update `pyproject.toml` and `uv.lock` together.

## Paired CY and queue check

When [selected](#acceptance-tiers), run `paired-check` against the final proposed versions
before the human merge, or the unchanged pair when no version change is expected; rerun if
inputs change. `CY_QUEUE_DIR` selects the cy-queue checkout (default `../cy-queue`), which
must be clean and contain its latest remote default branch. The stage installs both into a
temporary environment under `.tmp/`, runs `uv pip check`, the source and installed identity
check, the queue's Ruff, mypy, import contracts, tests and `cy-queue --help`, refuses if
either source changed meanwhile, reports both identities and removes the environment. A
failed or unavailable selected pairing blocks merge. CY never depends on the queue at
runtime; the queue raises its CY minimum when it adopts a newer interface.

## Releases

A human squash-merge of a PR into `master` releases code; there is no release PR or local
step. Because no CI job checks the PR (see the
[issue tracker](agents/issue-tracker.md#pr-grouping-and-delivery)), the selected
verification, independent review and pairing are complete before merge. The commit types
that bump the version are listed in [AGENTS.md](../AGENTS.md); the conventional parser
reads the commit messages inside a squash body as well as its title.

[release.yml](../.github/workflows/release.yml) runs on `pull_request_target` `closed`
events only for PRs merged into `master`, in one concurrency group that never cancels a
running release. It checks out `master` with full history and tags (closely spaced merges
may share one release), installs the pinned python-semantic-release and runs
`python -m scripts.release`, which:

1. requires a clean `master` checkout equal to remote `master` and one `origin` URL;
2. runs `semantic-release version --no-push --no-vcs-release`; its build command
   `python -m scripts.release_metadata` changes only the root package version in
   `uv.lock`, next to `project.version` and `CHANGELOG.md`;
3. succeeds without a commit or tag when no release is due;
4. otherwise validates one `chore(release): <version>` commit touching only those files
   ([release_lock_guard.py](../scripts/release_lock_guard.py)) with an annotated
   `v<version>` tag, refuses a moved remote `master` or an existing remote tag, pushes both
   refs with `git push --atomic --no-follow-tags`, and confirms both remote identities.

The job publishes only that commit and tag, as the release rule in
[AGENTS.md](../AGENTS.md) requires. It needs `GITHUB_TOKEN` with `contents: write` and
repository rules that let it push to `master`; if rules block it, arrange release-bot
authorization without weakening human protections. A rejected atomic push changes neither
ref. After a connection failure, inspect the remote refs
(`git ls-remote origin refs/heads/master 'refs/tags/v*'`) before rerunning the job
(`gh run rerun <run-id>`) on the refreshed `master`; an already published release reruns as
a no-op. Never overwrite a tag or reset unrelated work. Record on the Linear issue the run
URL, source and final SHAs, version or no-version result and confirmed tag identity.

## Model-weight releases

`weights-*` GitHub Releases are authorized separately (see [AGENTS.md](../AGENTS.md)) and
have their own cadence; reuse the current snapshot until its catalogue changes.

1. Inspect the eligible catalogue ([model assets](feature/model-assets.md)), native caches
   and upstream licence terms. Collect every applicable upstream licence and notice into
   one directory; those notices are authoritative.
2. Assemble the snapshot, choosing tag and notice directory deliberately:

   ```bash
   uv run --frozen --no-sync python scripts/package_weights.py \
     --output ./weight-release --tag weights-YYYY-MM-DD --notices ./weight-notices
   ```

   The output directory must be empty. The script writes one independent `.tar` per
   bundle, `manifest.json` and `SHA256SUMS`; any unresolved catalogue entry fails
   packaging. Each archive, including tar overhead and notices, stays under
   `--max-archive-bytes` (default 1,900,000,000 bytes), below the hosting size limit. It uploads
   nothing and changes no pin.
3. Include every applicable licence and attribution, source availability directions for
   AGPL assets and DEIMv2's non-commercial restriction. For DINOv3, preserve the exact
   bundled agreement, the separately linked Meta website agreement and the timm model
   card, and prominently display "Built with DINOv3" in the release notes and related
   product documentation. Retain genuine converted-checkpoint provenance and applicable use
   restrictions, original upstream identities and real Hub snapshot metadata; never derive
   a snapshot commit from a file hash.
4. Verify catalogue completeness, archive and member sizes and hashes, safe member names
   and offline native loading from a fresh cache.
5. Publish the manifest, checksums and every archive under a new tag marked GitHub Latest,
   and verify the hosted bytes against the manifest. Never replace published bytes; a
   correction is a new tag. Record the tag, sources, notices, checks and limitations on the
   Linear issue.
6. In a code PR, point `src/clearml_yolo/adapters/assets/weights-manifest.json` at the
   published manifest and run the architecture, behavior, pairing and review gates. The pin
   feeds preparation fingerprints. Packaging, mocked transport or an upload alone does not
   establish native restoration.
