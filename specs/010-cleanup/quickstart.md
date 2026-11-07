# Validation and execution guide

Run future implementation checks from its reconciled isolated source/environment.
Do not run publication or release commands merely to validate this planning package.

## Planning package

Pass the new Markdown files explicitly to `scripts/check_docs.py`; untracked files
are not selected by `--all`. Review requirement/task coverage and plan dependencies.

## Focused implementation checks

```bash
uv run --frozen --no-sync pytest tests/test_local_release.py tests/test_verify.py --durations=25
uv run --frozen --no-sync pytest tests/test_docs_validation.py tests/test_docs_isolation.py tests/test_export_workflow.py
uv run --frozen --no-sync pytest tests/test_config_tree.py tests/test_config_self_containment.py tests/test_architecture.py tests/test_tooling_boundaries.py
uv run --frozen --no-sync pytest tests/test_metrics.py tests/test_hub_assets.py tests/test_hub_weight_bundles.py
```

Capture the original failures before fixes. Preserve complete scenario coverage,
including deferred preview expressions, copy fallback and independent fixture state.

## Final implementation acceptance

```bash
uv run --frozen --no-sync python scripts/verify.py
uv run --frozen --no-sync python scripts/verify.py --docs
uv run --frozen --no-sync cy-docs --check
uv run --frozen --no-sync pytest browser_tests
```

The canonical run includes architecture negative cases and real CPU-DDP; do not
repeat them independently merely to claim another gate. Assess configured mutation
selection against actual changed files/tests/dependencies. Follow maintained paired
release procedures for normal CY/queue resolution, installed metadata, static checks,
integration tests and final versions; never use no-deps installation as acceptance.

Repeat fresh-cache offline restoration and native DINOv3 loading on final source
after Hub changes. Reuse unchanged archive/hash evidence only within its proven scope.
Require final independent review and full diff reconciliation. Compare dated baseline/final timings under equivalent conditions; report
skipped, unavailable and waived physical outcomes separately from passes.
