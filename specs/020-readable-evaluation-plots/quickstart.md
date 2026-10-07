# Verification guide

Run the focused adapter tests:

```bash
uv run pytest tests/test_interactive_evaluation.py tests/test_clearml_results.py tests/test_clearml_report.py tests/test_native_tracking_contract.py tests/test_native_ddp.py
```

Then run Ruff, mypy, import-linter and the full pytest suite as documented in
[development procedures](../../docs/development.md#verification).
Follow the [project E2E skill](../../.agents/skills/running-end-to-end-tests/SKILL.md)
for isolated run setup. With a baseline, inspect new Plots: class-series test PR;
grouped confusion modes; no baseline charts/comparison tables or native validation PR.
Toggle class legends and normalization; check empty-class legend statuses without
numerical points. Download comparisons and inspect durable baseline provenance.
