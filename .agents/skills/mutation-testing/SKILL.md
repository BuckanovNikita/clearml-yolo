---
name: mutation-testing
description: Use when reviewing mutation survivors or unreached functions, or changing mutation selection or settings.
---

# Triage mutation results

Paths start at the repository root. Read `docs/development.md#mutation-report` for the
command, budget and exit meanings, `[tool.mutmut]` in `pyproject.toml` for the settings,
and the module docstring of `scripts/mutation.py` for how functions and tests are selected.

1. Run the report over the whole product change: `--base master` for a task branch;
   without it the report covers only staged inputs.
2. Sort every reported function into one of: killed, survived, not reached by tests,
   not run (budget), skipped (function budget). Exit 2 is a tool, configuration or
   clean-test failure: diagnose it; it is never a result.
3. For each survivor, compare the mutant with the caller's observable contract,
   boundaries and effects:
   - unprotected behavior: strengthen a product test, stage it and rerun the affected
     functions;
   - equivalent or presentation-only mutant: keep the code and write the reasoning down.
   There is no survivor allowlist.
4. For unreached functions, decide whether a unit test can reach them or the behavior
   needs live or hardware execution, and name that check.
5. Record the base, selected functions and tests, outcomes, dispositions and reruns in
   the Linear issue. Done when every survivor and unreached function has a disposition.

Changes to the mutation tooling keep mutation product-only, staged inputs isolated,
selectors bounded, heavy and live tests excluded and owned processes cleaned up. Exercise
such changes with disposable command scenarios.
