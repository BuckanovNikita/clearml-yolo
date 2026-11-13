---
name: mutation-testing
description: Use when reviewing mutation survivors or unreached behavior, or changing mutation selection.
---

# Triage mutation evidence

Read `docs/development.md` (Mutation report). The Task and `[tool.mutmut]` configuration
own invocation, selection, budgets and exit meanings; paths start at the repository root.

1. Select the whole product change against its recorded base; staged reports cover
   only staged inputs.
2. Compare survivors with the caller's observable contract, boundaries and effects.
   Strengthen product tests for unprotected behavior, stage them and rerun affected
   mutations. Preserve correct code for equivalent or presentation-only mutants and
   record the reasoning; there is no survivor allowlist.
3. Separate survivors from unreached functions, unrun mutants and budget exclusions.
   Identify coverage requiring live/hardware execution. Diagnose failed clean baselines
   and tool errors rather than interpreting report production as successful coverage.
4. Record selected functions/tests, selection source, outcomes, dispositions and reruns
   in native evidence. Use `verification-workflow` to assess reuse and remaining gaps.

Changes to mutation tooling preserve product-only mutation, isolated staged inputs,
bounded selectors, heavy/live exclusions and owned-process cleanup. Exercise tooling
with disposable command scenarios; repository tests exercise product behavior.
