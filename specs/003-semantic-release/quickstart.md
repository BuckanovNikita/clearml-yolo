# Quickstart Validation

Initialize the existing pinned submodules, then install dependencies and hooks:

```bash
git submodule update --init --recursive
uv sync --locked --dev
uv run --locked --no-sync python scripts/local_release.py --install-hooks
```

Installation creates pre-commit and post-commit hooks without creating a release.
Use temporary repositories through the acceptance suite, not throwaway commits on master:

```bash
uv run pytest tests/test_local_release.py
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

Expected: fixture commits produce checked metadata commits and annotated tags; negative
cases preserve history and local work. See [the contract](contracts/local-release.md)
for retry behavior and [the README](../../README.md) for contributor instructions.
