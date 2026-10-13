# Validation guide

Use the prepared project development environment and approved external dependency copies.

```bash
uv run --frozen --no-sync ruff check .
uv run --frozen --no-sync mypy .
uv run --frozen --no-sync vulture
uv run --frozen --no-sync pre-commit run vulture --all-files
uv run --frozen --no-sync lint-imports
uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py
uv run --frozen --no-sync pytest
UV_NO_SYNC=1 uv run --frozen --no-sync pre-commit run --all-files
```

For a wider advisory scan, run `uv run --frozen --no-sync vulture --min-confidence 60`.
Inspect dynamic-use candidates before changing framework hooks or serialized fields.
See [the policy report](../../docs/static-analysis.md) and dated verification for
scope, negative-control checks and regression evidence.
