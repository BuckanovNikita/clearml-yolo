# Development and commit procedures

Read the relevant section before environment setup, code verification, dependency work or
any commit. The [agent instructions](../AGENTS.md) define authorization and task routing.
Read `pyproject.toml` for entrypoints, dependencies and import contracts.

## Verification

Use the repository's documented tooling and current check configuration. For code or
commit work, select the affected gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

Documentation-only work needs Markdown and local-link validation rather than the
application suite. Inspect [.pre-commit-config.yaml](../.pre-commit-config.yaml) before
running hooks: it includes changelog generation and a post-commit release hook.
The mocked suite cannot prove native training, a GPU or ClearML uploads; those require
dated real-run evidence and the
[end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md).

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
[CPU validation guide](../specs/010-native-clearml-integration/quickstart.md#cpu-distributed-regression-acceptance--2026-10-10-amendment)
for scope and evidence requirements; keep observed results in dated evidence.

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
callback and FiftyOne extension targets. Check distributions contain no removed queue
worker or project Hydra launcher plugin, and test standard sequential BasicLauncher sweeps.
Update maintained code links and migration guidance; preserve completed feature history as dated intent.

## External dependencies

`digital-metrics` and `report-generator` live in ignored local directories under
`external/`. They are ordinary source copies, not parent-repository submodules.
Copy the approved source trees to `external/digital-metrics` and
`external/report-generator` before installing dependencies. Independent clones at
these paths also work; do not add their contents or Git metadata to this repository.

| Dependency | Upstream | Approved source revision |
| --- | --- | --- |
| digital-metrics | [repository](https://github.com/Wasilkas/digital-metrics) | `7c6dfa98cc052ce0202f11655839078534182d77` |
| report-generator | [repository](https://github.com/Wasilkas/report-generator) | `8ddd0f7f11d25367f4e71ace77524ebb72257699` |

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

Commit only when requested. Stage explicit paths or hunks belonging to the task; preserve
unrelated staged and unstaged changes. Do not stash, reset, revert or bypass hooks to make
a check pass. Use Conventional Commits when committing.

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
commits alone do not bump the version. A failed post-commit hook does not undo the
original commit; inspect its output. To retry or check the release workflow manually:

```bash
uv run --locked --no-sync python scripts/local_release.py
```

After checking the result, push the branch and any newly created version tag explicitly.
Publish Git tags only; do not upload package assets. The
[release contract](../specs/003-semantic-release/contracts/local-release.md) describes
version policy, dirty-tree deferral, concurrency and recovery. The
[validation guide](../specs/003-semantic-release/quickstart.md) covers checks and changelog refresh.
