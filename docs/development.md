# Development and commit procedures

User-facing workflows are in the [README](../README.md); setup and operational
context are collected in the [technical reference](../TECH_DETAILS.md).

Read the relevant section before environment setup, code verification, dependency work or
any commit. The [agent instructions](../AGENTS.md) define authorization and task routing.
Read [pyproject.toml](../pyproject.toml) for package/dependency/release settings,
[ruff.toml](../ruff.toml) for lint policy and [.importlinter](../.importlinter) for import
contracts. Ruff and import-linter discover their dedicated files automatically.
The shared `python-code-standards` and `python-import-contracts` skills supply Python
requirements within the [native workflow](agent-workflow.md); this document owns the project's commands and
dependency/commit/release procedures.

## Python compatibility

The package supports Python `>=3.12.13,<3.14`. Development, Ruff and mypy retain
Python 3.12 as the oldest supported minor; `.python-version` selects the development
default rather than limiting installation to that minor. Verify packaging and the
routine suite on both Python 3.12 and 3.13 when changing interpreter compatibility.

Linux native execution additionally requires the existing pidfd, subreaper and
`/proc` capability checks. A Python version constraint cannot guarantee those
build/kernel capabilities. See [queue supervision](queue.md#guardians-cancellation-and-recovery).

## Runtime dependency compatibility

All CY runtime capabilities install by default, including the detector stack and
ONNX export. The separate `cy-queue` source package owns scheduling, the Textual TUI
and NVML; install it after CY into the same environment using
[queue installation](queue.md#installation). Neither distribution is assumed to be
available on PyPI. There are no project extras; remove
`--extra detectors`, `--extra export`, `--extra queue-ui` and corresponding package
extras from recipes. Keep development tools in `dependency-groups.dev`; required
upstream extras such as `rfdetr[train]` and `pandera[pandas]` remain runtime inputs.

[`pyproject.toml`](../pyproject.toml) owns direct lower bounds, exact pins and upper
bounds. The normal lockfile records the selected environment. When changing floors,
test an isolated `lowest-direct` resolution on Python 3.12.13 and 3.13, record the
resolved versions and executed checks in dated evidence, and raise a floor only
when compatibility evidence requires it. Resolution alone is not a runtime check.
Keep minimum-version resolutions separate from the normal lockfile, retain approved
external source revisions and avoid unrelated upgrades. TensorRT system requirements
remain external prerequisites. DEIMv2 source and non-YOLO pretrained assets can
resolve at execution through the [asset adapter](model-assets.md); explicit local
checkouts and files remain authoritative. Dependency installation is always external.

## Verification

[Taskfile.yml](../Taskfile.yml) owns verification commands and their order; prek owns
Git hooks and commit-message validation. Invoke every stage as:

```bash
uv run --frozen --no-sync task --exit-code <stage>
```

`--frozen --no-sync` runs Task in this worktree's prepared environment without
resolving or syncing, so uncommitted [source overrides](#external-dependencies) and
additional external runtime packages stay intact. `--exit-code` keeps each child
command's exit status. Clear an inherited `UV_PROJECT_ENVIRONMENT` before the outer
`uv run`; Task then pins the environment, testmon history, coverage data and Ruff/mypy
caches of its child commands to this worktree. Do not share these between worktrees.
Task freshness, timestamps and interrupted runs never establish completion. The
`verification-workflow` skill selects stages for a change and its completion report.

| Stage | Runs | Live |
| --- | --- | --- |
| `fix` | Safe Ruff fixes and `ruff format`; never stages files | no |
| `check` | Staged lock freshness, Ruff check and format check, import-linter, mypy, Vulture, deptry | no |
| `test` | Affected unit tests (testmon), excluding `tests/integration` | no |
| `test-full` | Every unit test; refreshes testmon history | no |
| `verify` | `check`, then `test`: development verification | no |
| `properties` | Unit suite under the Hypothesis `explore` profile, fixed order | no |
| `mutation` | Changed-function [mutation report](#mutation-report) | no |
| `infra-check` | Read-only, bounded stand preflight | read-only |
| `integration` | `infra-check`, then the non-GPU live tests, including the CPU stand smoke run | yes |
| `acceptance` | [Change acceptance](#acceptance-tiers) on a clean committed tip | yes |
| `release-acceptance` | [Release acceptance](#acceptance-tiers) | yes |
| `paired-check` | [Paired CY and queue release check](#paired-cy-and-queue-release-check) | no |
| `release-commit-check` | Checks of the version commit, run only by the [release tool](#local-releases) | no |

Unit stages run in parallel with `CY_TEST_WORKERS` workers (default 2) and
`--dist loadgroup`. Before heavy stages, inspect the host's reported load (for example
pcboard, where available) and lower the worker count or postpone the stage while the
user's workload needs the machine. No stage builds distributions. Development
verification never contacts live services.

`test` uses testmon affected selection under a history namespace derived from the
interpreter, the lockfile, verification configuration, test fixtures, package data and
tracked file membership; an unseen namespace starts a full baseline. Use `test-full`
when affected selection cannot represent a changed input. A deselected test is not a
fresh execution; report the actual selection.

### Lock freshness

The committed `pyproject.toml` declares `digital-metrics` and `report-generator` by
version only, while the committed `uv.lock` records them as editable copies under
`external/`. The committed project alone therefore cannot lock: without the source
override, uv would look the packages up on the index. [scripts/lock_check.py](../scripts/lock_check.py)
copies the **staged** `pyproject.toml`, `uv.lock` and `README.md` into a temporary
directory, appends the canonical [source override](#external-dependencies) when the
staged project declares no sources, links `external/` and runs `uv lock --check` there.
An uncommitted override in the working copy therefore never masks lock drift. The
check needs populated `external/` copies and never resolves into the worktree.

### Hooks and staging guard

Install the hooks once per worktree; the installer keeps the previous hooks for rollback:

```bash
bash scripts/install-hooks.sh
```

The pre-commit entry first runs the staging guard, `scripts/git-hook.sh`. It refuses the
commit when tracked changes are unstaged or nonignored untracked files exist, before prek
could stash anything; it never stages, stashes or deletes files. Its only exemption is
the documented local source override: an unstaged `pyproject.toml` whose working copy
differs from the index solely inside `[tool.uv.sources]`, optionally together with an
unstaged `uv.lock`. Every other unstaged or untracked input is refused.

prek then runs [.pre-commit-config.yaml](../.pre-commit-config.yaml): cheap hygiene hooks
(large files, merge conflicts, TOML/YAML syntax, end of file, whitespace,
`untracked-sources`) followed by one serial, always-run `verify` hook. The commit-msg
hook runs `conventional-pre-commit` with the allowed types `build`, `chore`, `ci`,
`docs`, `feat`, `fix`, `perf`, `refactor`, `style` and `test`. Heavy stages (live
integration, acceptance, property exploration, mutation) never run on commit.

Run `fix` explicitly before staging and inspect its changes. Intermediate commits may
defer development verification with `SKIP=verify`; the final committed content needs
`verify` with `SKIP` cleared. Reuse a passing commit-hook run while its inputs remain
unchanged. `uv run --frozen --no-sync prek run --all-files` remains the full hook check;
it runs the hygiene hooks over all files and `verify`. Rebase, cherry-pick and merge do
not run pre-commit hooks; verify combined content explicitly.

### Acceptance tiers

**Change acceptance** (`acceptance`) runs on a clean committed branch tip and refuses
uncommitted or untracked files before and after running. It runs `check`, `properties`,
the complete unit suite with coverage held at or above `[tool.coverage.report] fail_under`
in [pyproject.toml](../pyproject.toml), and the live part: `infra-check` followed by
`integration`, which includes the CPU smoke run against the shared ClearML stand. When
every path changed since `master` is Markdown or lies under `docs/` or `specs/`, the live
part is skipped and the stage says so. Code changes also need a mutation report against
`master` (`task mutation -- --base master`) and fresh independent review.

**Release acceptance** (`release-acceptance`) is required before a version is delivered.
It runs `acceptance`, then the GPU-marked tests with their `--run-*` options taken from
`CY_DDP_ARGS` and `CY_SEVERSTAL_ARGS`, the FiftyOne native-database tests in
`tests/integration/fiftyone` with `CY_TEST_FIFTYONE=1`, and `paired-check`. The real-run
gate on CPU and a single GPU remains a step of the
[end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md).

Report each required check as passed, failed, deferred, waived or error:

- **Deferred**: a temporarily unavailable resource, such as `infra-check` exit 3
  (unreachable stand, timeout or capacity wait) or a GPU busy with the user's workload.
  Deferred verification blocks acceptance, integration and release; continue independent
  local work and retry at a meaningful milestone.
- **Waived**: a check the user excused for this environment. Multi-GPU DDP on a
  single-GPU host is waived by standing decision; it never blocks.
- **Error**: `infra-check` exit 1, such as missing credentials, TLS trust or
  configuration. Diagnose it; do not wait or weaken security settings.

`infra-check` is bounded by `CY_INFRA_CHECK_TIMEOUT` (60 seconds by default) and creates
no run tag or resources. The `running-integration-tests` skill owns the live-run
lifecycle, run tags and exact-tag cleanup.

Finish environment provisioning before verification, including native SDK
optional decoders exercised by the selected tests. The installed Ultralytics image
fallback can request `pi-heif` for an unidentified image; provision that verification
prerequisite deliberately rather than relying on a mid-suite installation. Do not
install or update packages during a check. See the [static analysis policy](static-analysis.md)
for Ruff selections and exclusions, mypy boundary exceptions and Vulture's confidence
threshold.

Documentation-only work uses only native Spec Kit or OpenSpec documentation checks.
The mocked suite cannot prove native training, a GPU or ClearML uploads; those require
dated real-run evidence and the
[end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md).

### Native CPU distributed regression tests

The `ddp_cpu` suite runs real native YOLO training, validation and checkpoint creation
in two-rank and four-rank CPU/Gloo process groups. It belongs to the unit suite, so
`test-full` and both acceptance tiers run it; it shares the `serial` xdist group with the
process-supervision tests, so one worker runs those tests one at a time while other tests
stay parallel. To select it directly:

```bash
uv run --frozen --no-sync pytest -m ddp_cpu
uv run --frozen --no-sync pytest tests/test_native_ddp_cpu.py
```

Use the existing repository environment on Linux or WSL with Torch distributed/Gloo
support. Only unsupported platform or unavailable Gloo prerequisites may skip;
native runtime, process and callback failures remain failures. The suite creates
isolated synthetic data and randomly initialized models from the installed local
YOLOv8n architecture YAML, with no pretrained download, network access, GPU or
ClearML service requirement. Tests use a local recording task at the tracking
boundary while exercising the production owner relay.

Successful scenarios verify actual CPU/Gloo/DDP processes, parameter updates and
cross-rank synchronization, sampler partitions, live ordered owner-only telemetry
and one inference-loadable native best checkpoint. Worker and owner-callback
failure scenarios verify failed completion and cleanup of owned processes,
descendants and relay activity. Scenario execution is bounded by a 180-second
deadline and a 30-second process-group timeout; cleanup allows five seconds for
graceful shutdown before terminating only the owned process tree.

Test-only trainer adaptations retain installed native loops and do not add a
production CPU distributed launcher. Local task recordings establish callback
behavior and model association. Accelerator launch, NCCL, AMP and actual ClearML
uploads/downloads require separate acceptance; physical multi-GPU acceptance follows the
[DDP procedure](ddp-testing.md). Record observed results with their environment and
limitations.

### Generated and composed regressions

Hypothesis and pytest-cov are development dependencies. The routine suite stays offline;
generated CY cases exercise lexical CSV identity, prediction-cache provenance and
frozen validation thresholds. Queue state-transition cases live in cy-queue. Composed workflow tests join saved Hydra
configuration, real storage, evaluation and report boundaries. `HYPOTHESIS_PROFILE`
selects the deterministic default profile `clearml-yolo` or the larger `explore`
profile that the `properties` stage uses. To run these tests with branch coverage:

```bash
uv run --frozen --no-sync pytest tests/test_quality_properties.py tests/test_workflow_quality.py --cov=clearml_yolo --cov-branch --cov-report=term-missing --cov-report=html:.tmp/coverage/html
uv run --frozen --no-sync pytest -m process_capabilities
```

Coverage identifies unexercised paths; it does not establish assertion quality. Preserve
Hypothesis's reported falsifying example and reproduce a failure before changing its
seed or adding retries. pytest-randomly prints its seed; reproduce an order-dependent
failure with `--randomly-seed=<seed>`, or disable shuffling with `-p no:randomly`. The
local `.hypothesis/` example database is ignored by Git. Keep mutation/fault
observations and run counts in dated feature evidence.

Physical multi-GPU/NCCL and remote ClearML checks are opt-in under `ddp_gpu`; they and the
other GPU and FiftyOne live suites live in `tests/integration`, outside development
verification. Follow the [GPU DDP guide](ddp-testing.md) for exact selection,
prerequisites, deadlines and the evidence archive to return.

### Mutation report

`task mutation` mutates only the top-level functions and methods changed in the staged
diff (or against a named base) in a fresh workspace exported from the index, within a
budget of changed functions and seconds, and reports killed, surviving, unreached and
unrun mutants. `[tool.mutmut]` in [pyproject.toml](../pyproject.toml) holds the settings;
generated `mutants/` content is ignored by Git, Ruff and mypy and is outside Vulture's
maintained paths.

```bash
uv run --frozen --no-sync task --exit-code mutation                     # staged change
uv run --frozen --no-sync task --exit-code mutation -- --base master    # whole branch
```

Exit 0 is a report (survivors are advisory), 1 means survivors under `--strict`, and 2
is a tool error such as a failing clean test run; tool errors remain unresolved. Run it
explicitly for code changes before acceptance; it never runs in a commit hook and is
never cached. The `mutation-testing` skill owns survivor triage and settings invariants.
Keep dispositions in dated feature evidence.

### Static-analysis boundaries

Keep lint and stub distributions in the development group when adding runtime
dependencies. Review the tooling boundaries of `scripts/` when changing development
scripts. Ruff preview checks require explicit code selection; review the
[policy report](static-analysis.md) and refresh the rule inventory when changing the
locked Ruff version.

## Python integration and architecture

Use the [Python import migration](python-import-migration.md) when updating scripts or
saved Hydra targets. Workflows live in `application.use_cases` and require an explicit
`WorkflowDependencies` value. The composition root in `entrypoints.composition` creates
one dependency bundle per invocation; tests inject their own ports. Scientific core
code may use NumPy, pandas, SciPy, Pydantic and Pandera, but owns no SDK calls, logging
configuration, rendering or filesystem effects. Keep the pinned `digital-metrics`
algorithms in evaluation adapters and copy exact values into core evaluation records.

Run `lint-imports` and the complete ordinary suite, which contains the architecture tests, when changing imports, package initializers, composition or subprocess/plugin targets. Updating a dependency boundary also requires
regenerated YAML checks and installed command helps, including DDP callback and
FiftyOne extension targets. Check CY source installs include its bounded console
publisher, terminal mirror and FiftyOne worker; the queue source install must include
its guardian, snapshot runner and GPU probe. Verify CY has no cy_queue/Textual/NVML
imports, direct Hydra sweeps stay sequential, and queue tests preserve atomic batch
validation, deferred UI imports and owner-only jobs. Run the queue repository tests,
Ruff, strict mypy and import contracts in the combined environment when changing
the shared interfaces. Include negative import cases and both-package identity checks.
Check selected config export for every command/model selection, ordinary SDK configuration
with unchanged external selectors and project-contained application destinations, and retained project scratch after success, failure and
cancellation. Verify explicit project temp paths without changing global SDK temp defaults.
Check fresh DDP callback ownership and restored in-memory settings without settings-file writes.
Invalid dataset entries must be preserved and reported; native locks must not fall back to soft locks. Fault-inject real subprocess
hangs during import, publication and shutdown; require bounded optional warnings and
validated receipts, rather than inferred success. See [runtime isolation](runtime-isolation.md).
Update maintained code links and migration guidance; preserve completed feature history as dated intent.
For detector/export changes, include the runtime prerequisites and acceptance matrices in
the [model guide](multi-model-backends.md) and [deployment guide](tensorrt-deployment.md).
Use `uv run --frozen --no-sync` for verification in a deliberately prepared backend
environment so a default sync does not remove additional external runtime packages.

## External dependencies

The [shared evaluation and reporting guide](shared-evaluation-reporting.md) describes
the additive APIs used by application adapters and the retained compatibility wrappers.
Dependency source revisions change only through an explicitly authorized update, with
both legacy and new interface checks and application parity evidence.

`digital-metrics` and `report-generator` live in ignored local directories under
`external/`. They are ordinary source copies, not parent-repository submodules.
Copy the approved source trees to `external/digital-metrics` and
`external/report-generator` before installing dependencies. Independent clones at
these paths also work; do not add their contents or Git metadata to this repository.

| Dependency | Upstream | Approved source revision |
| --- | --- | --- |
| digital-metrics | [repository](https://github.com/Wasilkas/digital-metrics) | `6e801be1564dce458294eb23592cc1aa0939c4d9` |
| report-generator | [repository](https://github.com/Wasilkas/report-generator) | `7339ef864b4ff1b1db499a08d647193128088e80` |

The committed lockfile installs both paths editable; it does not store their source
contents or enforce their Git revisions. Keep the approved copies available for all
syncs and runs. A fresh checkout does not download them automatically. Once populated:

```bash
uv sync --frozen --dev
uv run --frozen cy --help
```

For local dependency resolution (for example `uv lock` or `uv sync` without `--frozen`),
add this uncommitted override to the working copy's `pyproject.toml`:

```toml
[tool.uv.sources]
digital-metrics = { path = "external/digital-metrics", editable = true }
report-generator = { path = "external/report-generator", editable = true }
```

Keep it unstaged and uncommitted; the [staging guard](#hooks-and-staging-guard) tolerates
exactly this difference and the [lock check](#lock-freshness) adds the same block to the
staged project. Follow the [commit procedure](#commit-procedure) for final acceptance.
Do not update upstream source revisions during ordinary setup. Existing submodule
users should preserve their populated source trees before switching to this revision;
remove only their obsolete `.git` pointer files and local `submodule.*` configuration.
Retaining `.git/modules/` preserves old dependency history for recovery.

`digital-metrics` is an external dependency. Keep it pinned to the approved upstream
revision. Do not change its source, checkout, dependency reference or locked revision
without the user's explicit intent to change it. General implementation,
cleanup and dependency maintenance requests do not authorize such changes. Adapt
`clearml-yolo` integration code when compatibility work is needed; report upstream
issues instead of patching or monkeypatching the dependency.

## Commit procedure

Commit when user or standing authorization covers the native completion workflow.
Explicit no-commit/no-release limits and the active host mode take precedence. Stage
explicit paths or hunks belonging to the task; preserve unrelated staged and unstaged
changes. Do not stash, reset, revert or bypass hooks to make a check pass. Use Conventional
Commits and inspect hook-generated changes before retrying.

Split work into coherent task-owned commits. Intermediate commits may use `SKIP=verify`
with final verification still outstanding; message validation and the staging guard stay
active. Keep mechanical formatting fixes in a separate commit. Do not use `--no-verify`
or blanket skips to hide failures. Run `verify` with `SKIP` cleared on the final content
(see [hooks](#hooks-and-staging-guard)); relevant subsequent changes invalidate affected
evidence.

Keep local `[tool.uv.sources]` overrides intact during intermediate commits, and never
stage them. Change acceptance needs a clean committed tip, which a checkout carrying an
override is not. Run it in a separate worktree at the final commit after confirming with
`git show HEAD:pyproject.toml` that the committed project has no source overrides.
Provision that worktree with its own `external/` copies and its own environment
(`uv sync --frozen --dev`): Task pins each stage to the worktree's `.venv`, and a shared
editable environment would import another checkout's sources. Do not resolve or update
dependencies during verification. Releases likewise run from a clean prepared checkout
without overrides; do not strip and restore overrides around each contributor commit.

## Paired CY and queue release check

Before every release or delivery of either repository, verify the latest CY and
[cy-queue](https://github.com/BuckanovNikita/cy-queue) together. Fetch both remotes
and inspect their latest default branches/tags, preserving unrelated local changes.
Use the intended release versions, including the version the release tool will
produce. A stale sibling checkout or editable installation is not current evidence.

With approved external dependencies prepared and active workers drained according to
[queue upgrade](queue.md#coordinated-package-upgrade), or in an isolated environment:

```bash
CY_QUEUE_DIR=../cy-queue uv run --frozen --no-sync task --exit-code paired-check
```

`CY_QUEUE_DIR` defaults to the sibling `../cy-queue` checkout. The stage fails when the
checkout is missing, installs both packages editable into this worktree's environment,
runs `uv pip check`, compares both source versions with the installed metadata, runs the
queue suite and `cy-queue --help`, and prints both commit SHAs and versions. Normal
resolution must succeed without `--no-deps`. Run the queue's configured static/import
checks too. Record both source SHAs, versions and actual results in dated task evidence.
If the release changes a version, refresh the installation and recheck the final pair
before pushing. Incompatibility, stale metadata, missing current sources or
unavailable/failed checks block delivery. The queue declares only a minimum compatible
CY version, never an upper bound; raise that minimum when the queue starts using a newer
CY interface. CY remains independent of the queue at runtime. `release-acceptance` runs
this stage; it is mandatory before delivering either package.

## Local releases

Code releases contain Git commits and annotated version tags only. Do not build,
upload or offer project `.whl` wheels or `.tar.gz` source archives as release
deliverables. Distribution builds and isolated archive installs are allowed only
for a concrete debugging purpose; they are not routine release acceptance gates.
Run release verification from the source checkout. Generic packaging guidance in
shared skills does not override this project rule. There is no CI.

python-semantic-release alone determines versions, changelog entries and annotated
`v{version}` tags from Conventional Commits: `fix` and `perf` produce a patch, `feat` a
minor, and breaking changes a minor below 1.0. Other types alone produce no version,
which is a successful outcome. Configuration lives in `[tool.semantic_release]` in
[pyproject.toml](../pyproject.toml). The [release skill](../.agents/skills/release/SKILL.md)
owns the procedure:

1. Accept the clean branch tip: `acceptance`, a mutation report against `master` for
   code changes, fresh independent review, and `release-acceptance` before delivery.
   Without push authorization, stop after reporting acceptance.
2. Under `flock -n "$(git rev-parse --git-common-dir)/clearml-yolo-release.lock"`:
   confirm the accepted tip and a clean tree, `git fetch origin`, switch to `master`,
   fast-forward to `origin/master` and then to the accepted tip, print the next version,
   run semantic-release with `CY_RELEASE_CHECK=1 SKIP=verify` and `--no-push
   --no-vcs-release`, and push `master` with `--follow-tags`. Confirm the refs with
   `git ls-remote`. A held lock is a reported blocker, never waited on or broken.

The version commit may change only `pyproject.toml`, `uv.lock` and `CHANGELOG.md`.
semantic-release's build command updates only the root `clearml-yolo` version in
`uv.lock` through `scripts/release_version.py`, without dependency resolution. With
`CY_RELEASE_CHECK=1` it then runs `release-commit-check`: staged paths limited to those
three files, no unstaged or untracked inputs, a `uv.lock` difference from `HEAD` limited
to the root package version (`scripts/release_lock_guard.py`), lock freshness, read-only
Ruff and deptry. `SKIP=verify` applies only to this version commit; message validation
and the staging guard remain active.

A failed attempt may leave this attempt's version, changelog and lockfile changes staged
without a commit or tag. Restore only those changes, fix the cause on the branch and
accept the new tip again. Never hand-edit versions or tags, and never tag a tip other
than the accepted one. Publish Git tags only for code: no code GitHub Releases, project
distribution assets or registry packages. The separate
[model-weight procedure](#model-weight-releases) is the only model-assets exception.

## Model-weight releases

The user-authorized model-assets exception permits `weights-*` GitHub Releases in
`BuckanovNikita/clearml-yolo` containing verified model-weight/source tar archives,
manifest, checksums and upstream notices. It does not authorize project wheels,
source distributions or registry packages. Weight tags have an independent cadence
from application versions; code releases neither package nor upload weights.
Reuse the current snapshot across code releases until its catalogue needs an update.

Inspect the current [eligible catalogue](model-assets.md#catalogue-and-automatic-execution),
native caches and upstream licence terms (the
[2026-10-29 licence inventory](https://github.com/BuckanovNikita/clearml-yolo/blob/91756fa4661c79854dacd7c827832854dc63e787/specs/009-release-weights/licenses.md) records those of the initial snapshot), then
assemble a complete snapshot with the explicit maintainer command:

```bash
uv run --frozen --no-sync python scripts/package_weights.py \
  --output ./weight-release --tag weights-YYYY-MM-DD --notices ./weight-notices
```

Replace the example date and notice directory deliberately. The script resolves the
eligible catalogue and writes independent `.tar` files, `manifest.json` and
`SHA256SUMS`; any unresolved entry fails packaging. Its default archive target is
1,900,000,000 bytes, including tar overhead and notices, below the 2 GiB hosting limit.
It performs no upload and does not change the runtime pin. Include every applicable
licence and attribution, source availability directions for AGPL assets, and DEIMv2's
non-commercial restriction. For DINOv3, preserve the exact bundled agreement,
the separately linked Meta website agreement and the timm model card; prominently
display “Built with DINOv3” in release notes and related product documentation.
Retain the genuine converted-checkpoint provenance and applicable use restrictions.
Preserve original upstream identities and real Hub
snapshot/configuration metadata; never fabricate a snapshot commit from a file hash.

Before publication, verify catalogue completeness, archive/member size and hashes,
safe members and fresh-cache offline native loading. Publish the manifest, checksum
file and all archives under the chosen new weight tag. Make the deliberate model
release visible as GitHub Latest so users can find its assets; runtime selection
still uses the packaged pin and never the moving latest endpoint. Verify the actual
hosted bytes against the manifest. Record the tag, sources, licence notices, executed checks
and limitations in dated feature evidence. Do not replace published bytes in place;
corrections use a new snapshot identity.

After verifying publication, deliberately update the packaged
`src/clearml_yolo/adapters/assets/weights-manifest.json` pin to that manifest and run
the applicable architecture, behavior, documentation, paired compatibility and
independent review gates before code delivery. The pin participates in automatic
preparation fingerprints. Packaging, mocked transport or an uploaded asset alone
does not establish successful native restoration or complete code-release acceptance.
