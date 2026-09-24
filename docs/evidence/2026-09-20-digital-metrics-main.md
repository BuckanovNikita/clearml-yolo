# digital-metrics upstream update — 2026-09-20

At the user's explicit request, switched the dependency from commit
`ecce79cdcade2bb463c4bcc9eac77512d1033117` (0.4.0) to upstream `origin/main`
commit `12fa6ce1b6ac4ab2b6db1f39e10f816a5849d068` (0.5.3).
The revision was verified with `git ls-remote` and `git fetch origin main`.
The exact commit remains pinned so routine resolution cannot advance it implicitly.
AGENTS.md now requires explicit user intent for future dependency changes.

`uv lock` and `uv sync --locked` succeeded. Installed distribution metadata confirmed
the requested Git commit. The external source checkout remained clean and unchanged.
The report-generator dependency and other locked packages were unchanged.

The first regression run passed 292 tests and failed one obsolete expectation:
greedy matching formerly dropped a false negative for a wrong-class prediction.
Upstream now uses class-aware assignment and preserves that miss. Updated the
clearml-yolo regression and explanation to reflect the upstream correction, without
changing dependency source or application scoring behavior.

The final `uv run --locked pre-commit run --all-files` passed all hooks, including
the 293-test suite, Ruff, mypy and import-linter. No live training or ClearML run
was performed for this dependency update.
