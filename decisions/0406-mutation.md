# ADR-0406 · Report mutation outcomes for changed product functions

A passing test suite can leave a changed decision unobserved. The mutation driver maps changed lines to functions, constructs an isolated working copy and selects candidate tests for those functions. An advisory run reports survivors and unreached functions for review. Strict mode can turn survivors into failure, while a tool failure has a distinct exit status.

The issue records a disposition for outstanding mutations. An advisory exit alone does not establish that every mutant was killed. [Mutation task](../Taskfile.yml) · [Selector and report](../scripts/mutation.py) · [Interpretation of exits](../AGENTS.md#checks)
