# Quickstart Validation

Populate the approved local dependency copies as described in the
[development guide](../../docs/development.md#external-dependencies), then install
dependencies and hooks:

```bash
uv sync --frozen --dev
uv run --locked --no-sync python scripts/local_release.py --install-hooks
```

Installation creates pre-commit and post-commit hooks without creating a release.
Use temporary repositories through the acceptance suite, not throwaway commits on master:

```bash
uv run --frozen pytest tests/test_local_release.py
uv run --frozen ruff check .
uv run --frozen mypy .
uv run --frozen lint-imports
uv run --frozen pre-commit run --all-files
```

Expected: fixture commits produce checked metadata/changelog commits and annotated tags; negative
cases preserve history and local work. See [the contract](contracts/local-release.md)
for retry behavior and [the development guide](../../docs/development.md) for contributor instructions.

Pre-commit regenerates CHANGELOG.md from existing history; if it changes, review and
stage the file, then retry the commit. Release preparation includes that commit's own
entry in the new version section. For a standalone refresh:

```bash
uv run --locked --no-sync python scripts/local_release.py --changelog
git diff -- CHANGELOG.md
git add -- CHANGELOG.md
```

The refresh exits 1 when it changes output (or reports an error), and 0 otherwise.
The generated file is not a place for manual notes. During recovery, retain the
prepared changelog and stage it with pyproject.toml and uv.lock; content changes
invalidate its checksum and block tagging. See the
[amendment evidence](../../docs/evidence/2026-09-30-changelog-release.md).
