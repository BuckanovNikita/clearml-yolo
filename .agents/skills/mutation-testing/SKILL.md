---
name: mutation-testing
description: Select and triage the changed-function mutation report, including survivors, unreached functions, tool failures and mutmut configuration changes.
---

# Changed-function mutation review

Use [the mutation Task](../../../Taskfile.yml) and its
[selection contract](../../../docs/development.md#mutation-report). The driver and
`[tool.mutmut]` own selectors, exclusions and budgets; inspect their help/configuration
when changing scope. For product changes before acceptance, use the branch comparison
against `master`; a staged report covers a different diff. Missing dependency data may
use the driver's import fallback; empty selection never launches mutmut.

Triage observable behavior, boundaries and effects:

1. Read each survivor against its caller's contract. Strengthen a product test when a
   changed outcome is unprotected, stage it and rerun the affected report.
2. Record equivalent or presentation-only mutants with their reasoning. Keep correct
   product code intact; there is no survivor allowlist.
3. Distinguish functions beyond the budget, mutants not run and functions not reached
   from surviving mutants. Explain when only live/hardware tests can reach a function.

A report's advisory success is not proof every mutation was killed. Strict mode fails
survivors and unreached functions; tool/configuration errors and a failed clean
baseline require diagnosis. No-mutant results can be valid for changes outside
mutmut's supported function bodies.

When changing settings, preserve product-only mutation, isolated staged inputs, bounded
selectors, live/heavy-test exclusions and owned-process cleanup. Validate the driver
with disposable command-level scenarios; repository tests exercise product behavior.

Record changed functions, selected tests and their selection source, budget exclusions,
killed/survived/not-reached/not-run results, survivor dispositions and rerun outcomes
in dated feature evidence. Reuse relevant successful evidence rather than rerunning an
unchanged stage.
