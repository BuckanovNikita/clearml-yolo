# Configuration simplification verification — 2026-10-19

## Scope and decisions

FR-006–008 extend feature 026 without rewriting its completed history. Parent inspection
and artifact analysis found coverage for all three requirements in T020–T026, no ambiguity,
no unmapped implementation tasks and no constitution conflict. Spec Kit extension hooks
were empty. Architecture plan validation passed before implementation.

Moved Ruff to `ruff.toml` and import contracts to `.importlinter`; retained small tool
settings, package metadata and semantic-release configuration in `pyproject.toml`.
The manifest decreased from 950 to 186 lines, including unchanged local uv overrides.
No dependencies, lock entries, package behavior or runtime modules were changed.

Ruff now selects `ALL` with lint preview; exclusions have adjacent reasons. Production
exceptions for Hydra private imports, FiftyOne plugin initialization, workbook XML and
integral float comparisons are restricted to their owning paths. Framework rules remain
active. Compared effective settings for a representative production module: 735 previously
enabled rules remain enabled and the new configuration enables 880. This number includes
preview rules and is specific to locked Ruff 0.16.1 and this path, not every file.

## Executed checks

- Existing Ruff baseline passed before edits; final `uv run --frozen --no-sync ruff check .`
  passed. JSON stdin probes detect F821, production S101 and newly enabled D200; a pytest
  assertion remains accepted. An initial text-output probe assumed numeric diagnostic
  labels and failed its harness assertion; JSON diagnostics corrected that harness.
- Compared native import-linter TOML and INI reader output after normalizing boolean
  spelling, singleton/empty lists and ignoring INI contract IDs: all 43 contracts and
  session options are semantically identical. Package and remaining tool TOML tables
  are equal to their pre-edit values, apart from the two extracted tables.
- `uv run --frozen --no-sync lint-imports`: 43 contracts kept, none broken.
- `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py`:
  269 passed, five upstream deprecation warnings. Existing graph-mutation tests use
  the native INI reader and reject forbidden imports and unclassified modules.
- `uv run --frozen --no-sync mypy .`: passed for 349 source files.
- `uv run --frozen --no-sync vulture`: passed.
- `uv run --frozen --no-sync pre-commit validate-config`: passed.
- `UV_NO_SYNC=1 uv run --frozen --no-sync pre-commit run lint-imports --files .importlinter`:
  passed, confirming native configuration changes trigger the hook.
- The pytest hook triggered by `.importlinter` executed the full suite: 3263 passed,
  30 skipped, 7 deselected, 133 warnings in 554.58 seconds. Pytest succeeded, but the
  hook wrapper returned 1 because the parent edited task documentation/configuration
  during execution. This is not a passing hook result; no test failure was reported.
- `uv run --frozen --no-sync python scripts/check_docs.py --all` with the new evidence
  path explicitly supplied: 510 Markdown files checked, zero issues.
- `git diff --check`: passed.
- Repeated the pytest hook with parent edits paused: exit 0, `Passed`. The earlier
  wrapper failure is resolved. No runtime source changed during this task.
- Native TOML/YAML, trailing-whitespace and end-of-file hooks passed for extracted
  configuration. Final narrowed Ruff exclusions were checked again; Ruff passed.
- Final documentation/link validation passed after review wording corrections.

These checks concern tooling and the current working tree. They do not establish new
GPU execution, ClearML publication or model accuracy outcomes.

## Documentation and preservation

Updated the maintained static-analysis policy and live import-contract pointers in
`docs/development.md`, `docs/agent-workflow.md`, `docs/current-contracts.md`,
`docs/import-boundaries.md` and `docs/module-architecture.md`. README, AGENTS and portable
usage guidance need no changes: command schemas and application behavior are unchanged.
Earlier feature specifications/inventories remain dated history.

The tree already contained unrelated ClearML cache/parameter/runtime work, tests and
user documentation. Task ownership is the delta from the captured pre-edit working tree,
not the whole Git diff. In particular, only configuration-reader hunks in
`tests/test_architecture.py` and the import-contract link in `docs/current-contracts.md`
belong here. Preserve local `[tool.uv.sources]`, protected dependency revisions, unrelated
staged/unstaged files and all pre-existing services.

## Review and delivery

Fresh native read-only reviewer `config_review` returned **ship** with no blocking
implementation findings. The reviewer independently compared remaining TOML metadata and
all native import contracts, verified Ruff selection/discovery and passing diagnostics,
reviewed architecture negative controls and hook triggers, and inspected the passing
stable-tree pytest-hook log. They did not rerun the full suite or assess unrelated runtime
changes. Review suggestions narrowed RUF027 to tests and PLC2801 to native runtime,
ResourceRequest validation and tests; final wording correctly identifies the frozen model.

Parent reconciliation covers the complete task delta: the two new configuration files,
extracted manifest sections, native reader fixture/test hunks, hook filters, six maintained
documentation files and feature 026 amendments/evidence. Runtime files, dependency locks,
existing ClearML changes and unrelated documentation/test hunks remain outside this task.
Architecture acceptance is recorded in the adjacent architecture.json.

`uv run --frozen --no-sync python scripts/local_release.py` returned exit 1 with
“Release deferred: dirty tracked worktree or index.” No contributor commit, version commit,
tag or push was made. The normal commit hook temporarily isolates staged changes; here the
pre-existing untracked tests/modules depend on unstaged tracked runtime changes, so that
would create a mixed task-only check tree. Delivery task T026 remains open until this work
can be integrated without disturbing that unrelated work. No checks or hooks were bypassed,
and no stash/reset was used. No deployment or package publication is part of this task.
