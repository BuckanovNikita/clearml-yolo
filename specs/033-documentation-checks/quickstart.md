# Documentation checker validation

From the checkout, use the prepared development environment:

```bash
uv run --frozen --no-sync python scripts/check_docs.py --all
uv run --frozen --no-sync python scripts/check_docs.py README.md docs/development.md
uv run --frozen --no-sync pytest tests/test_check_docs.py
```

Exit 0 means selected documents passed; exit 1 reports documentation findings;
exit 2 reports invocation or repository-discovery errors. Explicit paths are
relative to the current directory; `--root` selects another repository for testing.
All-file scope is defined in [FR-005](spec.md#requirements). Links to excluded
files are still checked for existence and Markdown anchors when referenced.

The command neither fetches external links nor executes fenced examples. It checks
fence closure, not example correctness; render Mermaid diagrams separately.
