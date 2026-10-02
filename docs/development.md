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

## External dependencies

`digital-metrics` and `report-generator` live in `external/` as Git submodules.
Both track upstream `main` through `.gitmodules`; `git submodule update --remote`
advances their checkouts when an upstream update is requested.
Initialize them with `git submodule update --init --recursive` before `uv sync`.
Local development installs them editable through uncommitted `[tool.uv.sources]`
overrides, restored after each commit by the [commit procedure](#commit-procedure); the parent repository's
gitlinks pin their revisions. For installations without submodules,
users can select Git URLs and branches per README.md. Git sources use
`branch = "main"` (or `master` for a user-selected repository); `uv.lock` records
the resolved commits.

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
# Local development uses the pinned submodules. For other environments, replace
# these with Git sources via `uv add`; see the installation instructions in README.md.
digital-metrics = { path = "external/digital-metrics", editable = true }
report-generator = { path = "external/report-generator", editable = true }
```

Preserve the exact local section before removing it. Stage only the section removal
and other authorized changes; verify that the staged `pyproject.toml` has no
`[tool.uv.sources]` section. Preserve unrelated staged and unstaged edits. Run the
applicable commit checks without bypassing hooks. This temporary removal does not
authorize dependency resolution, changes to `uv.lock`, or submodule updates.

After the commit command and its hooks finish, restore the saved section locally
without staging it. Keep the section absent throughout any automatic release commit.
Restore it on failed or interrupted commit attempts as well; remove it again before
retrying. Verify that the working copy has the local overrides and that a successful
commit contains no `[tool.uv.sources]` section.
