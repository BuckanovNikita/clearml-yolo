# Plan: Plain prek hooks with cached pytest

Inputs: [specification](spec.md). Ledger: [tasks](tasks.md). Architecture record:
[architecture.json](architecture.json).

## Technical context

- Python `>=3.12.13,<3.14`, uv, Ruff, strict mypy, Vulture, import-linter and pytest.
- New dev tools: `prek` (Rust runner that reads `.pre-commit-config.yaml`) and
  `pytest-testmon`.
- No `src/` change. Only maintenance tooling, hook configuration, tooling tests and
  guidance change.

## Design

### Hooks

`.pre-commit-config.yaml` keeps the `pre-commit-hooks` hygiene hooks, `changelog` and
the post-commit `local-release` hook. The `verify` hook becomes these local system
hooks, which run serially in configuration order:

| ID | Command | Runs when staged files include |
| --- | --- | --- |
| `untracked-sources` | fails on untracked files under `src/`, `tests/`, `scripts/` | always |
| `ruff` | `ruff check .` | always |
| `mypy` | `mypy .` | always |
| `vulture` | `vulture` | always |
| `import-linter` | `lint-imports` | always |
| `pytest-full` | `pytest --testmon-noselect` | non-Python files under `src/`, `tests/` or `scripts/`, or `pyproject.toml`, `uv.lock`, `ruff.toml`, `.importlinter`, `.pre-commit-config.yaml` |
| `pytest` | `pytest --testmon` | always |
| `check-docs` | `python scripts/check_docs.py --all` | always |

When both pytest hooks are selected, `pytest-full` runs first and refreshes the testmon
database, so `pytest` then selects nothing. Static and testmon hooks always run
because staged file lists omit deletions (review finding B1). prek stashes unstaged
changes to tracked files; `untracked-sources` covers the untracked case that the
verifier's index/worktree comparison used to reject (finding B2). Both pytest entries
unset `PYTEST_ADDOPTS`.

### Release commits

`scripts/local_release.py` sets
`SKIP=ruff,mypy,vulture,import-linter,pytest-full,pytest` in the environment of its
own `git commit --only` and of the tag-recovery `prek run`. `validate_metadata` and
`validate_release_commit` already prove that this commit changes only the root
version bytes and `CHANGELOG.md`.

### Hook installation

`install_hooks` refuses an existing pre-commit hook that pre-commit or prek did not
generate, then runs `<interpreter bin>/prek install --hook-type pre-commit --force`
so a generated hook is replaced rather than chained as `pre-commit.legacy`. The
post-commit launcher runs `prek run --stage post-commit --all-files`; its
marker-based ownership check is unchanged.

## Architecture

Record: [architecture.json](architecture.json). The affected module is
`scripts/local_release.py`. It is maintenance tooling and must not import application
runtime, SDK or analysis packages. After this change it no longer imports
`scripts.verify`. `tests/test_tooling_boundaries.py` enforces this through the
`release_import_findings` allowlist, with its negative syntax cases.
`tests/test_tooling_boundaries.py` also keeps analysis tools out of runtime
dependencies; `prek` and `pytest-testmon` join that list.

## Verification

- Testmon go/no-go: a full `pytest --testmon-noselect` run, timed against the
  roughly 16.5-minute baseline, followed by an unchanged `pytest --testmon` run.
- Focused: `tests/test_local_release.py`, `tests/test_tooling_boundaries.py`.
- Full: Ruff, mypy, Vulture, import-linter, `pytest --testmon-noselect`,
  `prek run --all-files`, `python scripts/check_docs.py --all`.
- Cache behaviour on staged Python, non-Python and documentation-only changes;
  the real commit and release-commit hook output.
