---
name: mutation-testing
description: Use when reviewing mutation survivors, unreached functions or tool failures, or changing mutmut configuration.
---

# Review changed-function mutations

Read `docs/development.md` (Mutation report); `Taskfile.yml` owns invocation.
Paths start at the repository root. The driver and `[tool.mutmut]` own selectors,
exclusions and budgets; inspect help/configuration before changing scope.

1. For product acceptance, select the branch comparison against `master`. Staged
   reports cover a different diff. Missing dependency data may use the driver's
   import fallback; empty selection launches no mutmut process.
2. Read each survivor against its caller's contract, boundaries and effects. Add a
   product test for an unprotected outcome, stage it and rerun the affected report.
   Record equivalent/presentation-only mutants with reasons; preserve correct product
   code. There is no survivor allowlist.
3. Distinguish survivors, unreached functions, unrun mutants and budget exclusions.
   Explain live/hardware-only reachability. Advisory success does not mean every
   mutation died; strict mode fails survivors and unreached functions. Diagnose tool
   errors and failed clean baselines. Unsupported function-body changes may yield
   valid no-mutant results.
4. Record changed functions, selected tests/selection source, budgets, dispositions
   and killed/survived/not-reached/not-run/rerun outcomes in dated evidence. Reuse
   successful checks while their inputs remain unchanged.

When changing settings, retain product-only mutation, isolated staged inputs, bounded
selectors, live/heavy-test exclusions and owned-process cleanup. Validate the driver
with disposable command-level scenarios; repository tests exercise product behavior.
