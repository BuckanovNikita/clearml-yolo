# Validation Guide

Use Python 3.12 and the locked project environment. Populate the approved local
dependency copies following the [development guide](../../docs/development.md#external-dependencies)
first; current setup no longer uses submodules.

```bash
uv sync --frozen --group dev
uv run --frozen cy-init-config ./conf
uv run --frozen cy-train --config-dir=./conf --config-name=cy-train --cfg job \
  ground_truth=ground_truth.csv
uv run --frozen cy --config-dir=./conf --config-name=cy --cfg job \
  ground_truth=ground_truth.csv
```

The last two commands only compose settings. They do not train or create a task.
Replace required inputs and set explicit ClearML identity before real execution.

Initialization writes eight command examples and the two native group files. Repeat
initialization: it must fail without replacing examples. Use `--force` only to discard
edits to generated files. Unrelated files must survive.

```bash
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen mypy .
uv run --frozen lint-imports
uv run --frozen pre-commit run --all-files
uv build
```

Install the wheel and source archive into separate fresh environments, supplying the
exact upstream Git requirements in the [release notes](../../docs/releases/0.3.0.md).
These installations must not depend on editable local dependency paths. Check all nine
command helps, example generation, collision/force behavior, and
composition through all eight execution commands. Scan first-party Python for the
prohibited import. Do not scan or modify external dependency checkouts.

Follow the [end-to-end skill](../../.agents/skills/running-end-to-end-tests/SKILL.md)
and the installation's environment guidance for isolated CPU/GPU runs, artifact retrieval,
and cleanup. Keep fresh evidence separate from historical release results.

The v0.3.0 publication workflow reviewed explicit task paths, verified the remote tag's
commit, and downloaded assets to compare SHA-256 hashes with the checked local artifacts.
Its dated results are in
[release evidence](../../docs/evidence/2026-09-28-release-030.md).
