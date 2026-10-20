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

All supported runtime capabilities install by default, including the detector
stack, ONNX export and the queue TUI. There are no project extras; remove
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
and the DEIMv2 checkout remain external prerequisites.

## Verification

Use the repository's documented tooling and current check configuration. For code or
commit work, select the affected gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run vulture
uv run lint-imports
uv run --frozen --no-sync python scripts/check_docs.py --all
uv run pre-commit run --all-files
```

See the [static analysis policy](static-analysis.md) for Ruff selections and exclusions,
mypy boundary exceptions and Vulture's confidence threshold. The Vulture hook scans
source, scripts and tests together using the locked development environment. Install
the updated dev dependencies before running it; for a deliberately prepared environment
with additional external runtime packages, use an inexact sync to preserve them.

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
and the existing pytest commit hook. To select it directly:

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
generated cases exercise queue state transitions, lexical CSV identity, prediction-cache
provenance and frozen validation thresholds. Composed workflow tests join saved Hydra
configuration, real storage, evaluation and report boundaries. To run these tests with
branch coverage:

```bash
uv run --frozen --no-sync pytest tests/test_quality_properties.py tests/test_workflow_quality.py --cov=clearml_yolo --cov-branch --cov-report=term-missing --cov-report=html:.tmp/coverage/html
uv run --frozen --no-sync pytest -m 'process_capabilities or gpu_controls'
```

Coverage identifies unexercised paths; it does not establish assertion quality. Preserve
Hypothesis's reported falsifying example and reproduce a failure before changing its
seed or adding retries. The local `.hypothesis/` example database is ignored by Git.
Keep mutation/fault observations and run counts in dated feature evidence.

Physical multi-GPU/NCCL and remote ClearML checks are opt-in under `ddp_gpu`, separate
from the routine suite and existing `ddp_cpu` tests. Follow the [GPU DDP guide](ddp-testing.md)
for exact selection, prerequisites, deadlines and the evidence archive to return.

### Static-analysis boundaries

The release helper imports only the standard library, Loguru and Pydantic. Keep lint
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

Run `lint-imports` and the architecture tests when changing imports, package initializers,
composition or subprocess/plugin targets. Updating a dependency boundary also requires
regenerated YAML checks and installed command helps, including the GPU probe, DDP
callback and FiftyOne extension targets. Check distributions include the queue guardian/snapshot runner, bounded console publisher,
terminal mirror and FiftyOne worker. Verify direct commands have no queue/Textual imports,
sequential Hydra sweeps, queue batch validation, optional UI imports and owner-only jobs.
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

Preserve the exact local section before removing it. Stage only the section removal
and other authorized changes; verify that the staged `pyproject.toml` has no
`[tool.uv.sources]` section. Preserve unrelated staged and unstaged edits. Run the
applicable commit checks without bypassing hooks. This temporary removal does not
authorize dependency resolution, changes to `uv.lock`, or dependency source updates.

After the commit command and its hooks finish, restore the saved section locally
without staging it. Keep the section absent throughout any automatic release commit.
Restore it on failed or interrupted commit attempts as well; remove it again before
retrying. Verify that the working copy has the local overrides and that a successful
commit contains no `[tool.uv.sources]` section.

## Local releases

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
