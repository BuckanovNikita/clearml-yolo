# Acceptance guide

Use the existing locked development environment and preserve external source copies. Remove local uv overrides exactly as described in [the commit procedure](../../docs/development.md#commit-procedure) before final verification; retain their backup until commit/release hooks finish.

```bash
uv run --frozen --no-sync python scripts/verify.py --force
uv run --frozen --no-sync python scripts/verify.py --docs
uv run --frozen --no-sync mutmut run 'clearml_yolo.core.*'
uv run --frozen --no-sync mutmut results
```

Inspect mutation outcomes and private verifier logs; do not infer success from a mutation exit code. A second unchanged verifier call must reuse evidence. Temporary-Git tests cover contributor/version/tag recovery without publishing test repositories. Complete independent review, architecture acceptance and the existing Git-tag release workflow, restoring overrides afterward even on failure.
