# Development and commit procedures

User-facing workflows are in the [README](../README.md); setup and operational
context are collected in the [technical reference](../TECH_DETAILS.md).

Read the relevant section before environment setup, code verification, dependency work or
any commit. The [agent instructions](../AGENTS.md) define authorization and task routing.
Read [pyproject.toml](../pyproject.toml) for package/dependency/release settings,
[ruff.toml](../ruff.toml) for lint policy and [.importlinter](../.importlinter) for import
contracts. Ruff and import-linter discover their dedicated files automatically.
The shared `python-project-workflow` skill supplies lifecycle requirements within the
[native workflow](agent-workflow.md); this document owns the project's commands and
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

Use one canonical entrypoint for ordinary verification and hooks:

```bash
uv run --frozen --no-sync python scripts/verify.py
uv run --frozen --no-sync python scripts/verify.py --force
uv run --frozen --no-sync python scripts/verify.py --docs
uv run --frozen --no-sync pre-commit run --all-files
```

The default runs Ruff, strict mypy, Vulture, import-linter and one complete ordinary
pytest suite. That pytest run includes architecture negative cases and native CPU-DDP;
no additional architecture or full-suite invocation is needed to satisfy those gates.
Focused commands remain useful while developing. `--force` requires fresh ordinary
checks. `--docs` validates documentation separately, including new governed Markdown.
Documentation validation runs fresh because link-target existence can change independently.

Successful application checks record commands, results and log references in Git-private
storage. Reuse requires matching governed source, tests, fixtures, package data, check
configuration, lockfile, interpreter, installed dependency file identities, editable
contents and test-affecting environment, including new/untracked inputs. Environment
values are digested rather than logged. Git hook invocation noise is normalized in
the actual check environment; nonempty `PYTEST_ADDOPTS` is rejected so selection flags
cannot turn ordinary acceptance into a partial or collection-only run. Success is written atomically only after all
checks pass and a second input snapshot is unchanged. Missing, malformed, stale,
failed or interrupted evidence runs fresh checks. Hook checks reject an index/worktree
view mismatch; partial staging or path-limited commits cannot borrow success for a
different file view. Ignored root files and nested fixtures are also fingerprinted.
Ignored local fixture data is treated as an external input; code and checking
configuration must match the staged view. Documentation-only evidence updates do not invalidate application
checks. Keep local receipts/logs private; dated feature evidence records outcomes.

See the [static analysis policy](static-analysis.md) for Ruff selections and exclusions,
mypy boundary exceptions and Vulture's confidence threshold. Install the locked dev
dependencies before verification; in a deliberately prepared environment, an inexact
sync preserves additional external runtime packages.

Documentation-only work needs Markdown and local-link validation rather than the
application suite. Inspect [.pre-commit-config.yaml](../.pre-commit-config.yaml) before
running hooks: it includes changelog generation and a post-commit release hook.
The mocked suite cannot prove native training, a GPU or ClearML uploads; those require
dated real-run evidence and the
[end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md).

`scripts/check_docs.py --all` reads tracked project Markdown, checking local paths,
GitHub-style anchors (including duplicate/Unicode headings), reference links and
fences. Pass new file paths explicitly before staging. It excludes generated changelogs,
symlinks and installed workflow assets; it never fetches external links, executes
examples or rewrites files. See the [checker contract](../specs/000-baseline/spec.md#verification-and-delivery-requirements)
for scope and exit codes. Mermaid grammar needs a separate render and visual review.

### Native CPU distributed regression tests

The `ddp_cpu` suite runs real native YOLO training, validation and checkpoint creation
in two-rank and four-rank CPU/Gloo process groups. It is included in `uv run pytest`
and the canonical verification commit hook. To select it directly:

```bash
uv run pytest -m ddp_cpu
uv run pytest tests/test_native_ddp_cpu.py
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
uploads/downloads require separate acceptance. See the
[CPU validation guide](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle)
for scope and evidence requirements; keep observed results in dated evidence.

### Generated and composed regressions

Hypothesis and pytest-cov are development dependencies. The routine suite stays offline;
generated CY cases exercise lexical CSV identity, prediction-cache provenance and
frozen validation thresholds. Queue state-transition cases live in cy-queue. Composed workflow tests join saved Hydra
configuration, real storage, evaluation and report boundaries. To run these tests with
branch coverage:

```bash
uv run --frozen --no-sync pytest tests/test_quality_properties.py tests/test_workflow_quality.py --cov=clearml_yolo --cov-branch --cov-report=term-missing --cov-report=html:.tmp/coverage/html
uv run --frozen --no-sync pytest -m process_capabilities
```

Coverage identifies unexercised paths; it does not establish assertion quality. Preserve
Hypothesis's reported falsifying example and reproduce a failure before changing its
seed or adding retries. The local `.hypothesis/` example database is ignored by Git.
Keep mutation/fault observations and run counts in dated feature evidence.

Physical multi-GPU/NCCL and remote ClearML checks are opt-in under `ddp_gpu`, separate
from the routine suite and existing `ddp_cpu` tests. Follow the [GPU DDP guide](ddp-testing.md)
for exact selection, prerequisites, deadlines and the evidence archive to return.

### Scoped mutation acceptance

The locked mutmut 3.8.x development dependency assesses training-box validation,
evaluation policy and core export quality. `[tool.mutmut]` defines the exact source,
offline test selection and copied fixtures. Native training, GPU, remote publication
and release machinery are excluded. Generated `mutants/` content is ignored by Git,
Ruff and mypy and is outside Vulture's maintained paths.

```bash
uv run --frozen --no-sync mutmut run 'clearml_yolo.core.*'
uv run --frozen --no-sync mutmut results
uv run --frozen --no-sync mutmut run 'clearml_yolo.core.evaluation.policy*'
uv run --frozen --no-sync mutmut show MUTANT_NAME
```

At acceptance, rerun affected selected modules when their code, selected tests, fixtures
or dependencies change. Use explicit module/function selection for incremental work;
an explicit selection reruns cached verdicts, while bare `mutmut run` may reuse them.
Clear only task-owned stale mutant output when source/test/dependency changes require
fresh execution. Broader audits are explicit. Mutation never runs inside contributor
or version-commit hooks. Report its outcomes separately from ordinary pytest success.
Every survivor needs stronger assertions or a reviewed equivalence explanation bound
to the tested inputs. Untested mutants, timeouts and runner errors remain acceptance
gaps regardless of command exit status. Keep the baseline and individual dispositions
in dated feature evidence, not this evergreen guide.

### Static-analysis boundaries

The release helper imports the standard library, Loguru, Pydantic and the verifier's
shared byte-exact version validation. The verification entrypoint uses only the standard library and never imports application runtime modules. Keep lint
and stub distributions in the development group when adding runtime dependencies.
`tests/test_tooling_boundaries.py` enforces these constraints with
injected forbidden imports and dependency declarations. Ruff preview checks require
explicit code selection; review the [policy report](static-analysis.md) and refresh
the rule inventory when changing the locked Ruff version.

## Python integration and architecture

Use the [Python import migration](python-import-migration.md) when updating scripts or
saved Hydra targets. Workflows live in `application.use_cases` and require an explicit
`WorkflowDependencies` value. The composition root in `entrypoints.composition` creates
one dependency bundle per invocation; tests inject their own ports. Scientific core
code may use NumPy, pandas, SciPy, Pydantic and Pandera, but owns no SDK calls, logging
configuration, rendering or filesystem effects. Keep the pinned `digital-metrics`
algorithms in evaluation adapters and copy exact values into core evaluation records.

The canonical verification runs `lint-imports` and the architecture tests within its
ordinary suite when changing imports, package initializers, composition or subprocess/plugin targets. Updating a dependency boundary also requires
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
| report-generator | [repository](https://github.com/Wasilkas/report-generator) | `d10aa395d08f738e92e04e076cee93b3a993bf8f` |

The committed lockfile installs both paths editable; it does not store their source
contents or enforce their Git revisions. Keep the approved copies available for all
syncs and runs. A fresh checkout does not download them automatically. Once populated:

```bash
uv sync --frozen --dev
uv run --frozen cy --help
```

For local dependency resolution, use the uncommitted `[tool.uv.sources]` overrides
below. Restore them after each commit using the [commit procedure](#commit-procedure).
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

Before every commit, temporarily remove the entire `[tool.uv.sources]` section
from `pyproject.toml`, including its comments and the local editable overrides:

```toml
[tool.uv.sources]
# Local development uses ordinary dependency copies.
digital-metrics = { path = "external/digital-metrics", editable = true }
report-generator = { path = "external/report-generator", editable = true }
```

Preserve the exact local section before removing it. Perform final canonical verification
after removal and keep the section absent through independent review and automatic
release. This permits the same success receipt to cover those unchanged inputs. Stage only the section removal
and other authorized changes; verify that the staged `pyproject.toml` has no
`[tool.uv.sources]` section. Preserve unrelated staged and unstaged edits. Run the
applicable commit checks without bypassing hooks. This temporary removal does not
authorize dependency resolution, changes to `uv.lock`, or dependency source updates.

After the commit command and its hooks finish, restore the saved section locally
without staging it. Keep the section absent throughout any automatic release commit.
Restore it on failed or interrupted commit attempts as well; remove it again before
retrying. Verify that the working copy has the local overrides and that a successful
commit contains no `[tool.uv.sources]` section.

## Paired CY and queue release check

Before every release or delivery of either repository, verify the latest CY and
[cy-queue](https://github.com/BuckanovNikita/cy-queue) together. Fetch both remotes
and inspect their latest default branches/tags, preserving unrelated local changes.
Use the intended release versions, including any version the local release hook will
produce. A stale sibling checkout or editable installation is not current evidence.

With approved external dependencies prepared and active workers drained according to
[queue upgrade](queue.md#coordinated-package-upgrade), or in an isolated environment:

```bash
uv pip install --python .venv/bin/python -e . -e ../cy-queue
uv pip check --python .venv/bin/python
# Run from the queue repository so its own configuration is selected:
cd ../cy-queue
uv run --frozen --no-sync --project ../clearml-yolo pytest -q
uv run --frozen --no-sync --project ../clearml-yolo cy-queue --help
```

Run the queue's configured static/import checks and CY's applicable verification too.
Queue installation tests verify source/installed versions and dependency constraints;
normal resolution must succeed without `--no-deps`. Record both source SHAs, versions
and actual integration results in dated task evidence. If hooks change a version,
refresh the installation and recheck the final pair before pushing. Incompatibility,
stale metadata, missing current sources or unavailable/failed checks block delivery.
Update the queue's bounded requirement only after verifying the new CY interfaces;
do not assume an untested future minor is compatible. CY remains independent of the
queue at runtime. This is a mandatory release acceptance step alongside the hooks.

## Local releases

Releases contain Git commits and annotated version tags only. Do not build,
upload or offer project `.whl` wheels or `.tar.gz` source archives as release
deliverables. Distribution builds and isolated archive installs are allowed only
for a concrete debugging purpose; they are not routine release acceptance gates.
Run release verification from the source checkout. Generic packaging guidance in
shared skills does not override this project rule.

After installing dependencies, install both repository hooks:

```bash
uv run --locked --no-sync python scripts/local_release.py --install-hooks
```

The installer preserves unrelated hooks and refuses to overwrite an existing custom
post-commit hook. Pre-commit regenerates CHANGELOG.md from committed history. If that
changes the file, inspect and stage the generated change, then retry the commit.
Do not edit the generated changelog by hand.

On master, the post-commit hook evaluates unreleased Conventional Commits. Release
changes produce a checked version commit and an annotated version tag. Documentation
commits alone do not bump the version. Release preparation updates only the root
package version in `uv.lock`; it does not resolve dependencies. The committed dependency
sources, versions and metadata remain unchanged while local source overrides are absent.
Generated version commits may reuse source verification only after validating the exact
expected source parent, the three release paths, root-version-only metadata changes and
the prepared changelog hash. Tag recovery retains metadata, ownership, concurrency and
conflicting-tag checks; a commit message alone never authorizes reuse.
A failed post-commit hook does not undo the
original commit; inspect its output. To retry or check the release workflow manually:

```bash
uv run --locked --no-sync python scripts/local_release.py
```

After checking the result, complete authorized delivery by pushing the intended branch
and any newly created version tag explicitly, then verify the remote refs. A no-release
evaluation is a valid outcome for documentation-only history; do not force a version bump.
Publish Git tags only: no GitHub Releases, release assets or registry packages. The
[release contract](../specs/000-baseline/spec.md#local-release-interface) describes
version policy, dirty-tree deferral, concurrency and recovery. The
[validation guide](../specs/000-baseline/spec.md#local-release-interface) covers checks and changelog refresh.
