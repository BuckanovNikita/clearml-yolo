# Bug Assessment: architecture check blind spots

- **Slug**: architecture-check-blindspots
- **Created**: 2026-10-15
- **Source**: user implementation plan, delegated bounded architecture-check work
- **Verdict**: valid
- **Severity**: medium

## Report

The architecture helpers accept nonexistent runtime attributes and miss definition-time
initializer operations and scoped filesystem, network, process and environment effects.
The checks therefore give false assurance; this assessment does not establish an
application-runtime defect or change scientific behavior.

## Reproduction

On 2026-10-15, an offline Python probe called the existing helpers with parsed snippets.
All of the following incorrectly returned an empty finding list:

| Guard | Reproduced input |
| --- | --- |
| Runtime target | `probe.local` for a variable defined only inside `outer()` |
| Runtime target | `probe.nested` for a function defined only inside `outer()` |
| Runtime target | `probe.Worker.missing` with only `Worker.run` defined |
| Initializer | `def lazy(x=initialize()): pass` |
| Initializer | `@initialize()` on a function definition |
| Initializer | `class Lazy(load_base()): pass` |
| Initializer | `class Lazy(metaclass=load_meta()): pass` |
| Core effects | `import os; value = os.environ["HOME"]` |
| Core effects | `import requests as net; net.get("https://example.org")` |
| Core effects | `from shutil import copyfile as copy; copy("a", "b")` |

## Root Cause and Remediation

Confidence: high. `tests/architecture_helpers.py` collects every descendant binding
as a module symbol and checks only the first attribute segment. Initializer traversal
skips complete function definitions and class headers. Effect detection matches call
leaf names, with a module-wide import-alias dictionary that ignores lexical scope.

Implement scope-aware declaration/re-export resolution, inspect definition-time
expressions without descending into deferred function/lambda bodies, and resolve
known effect families through scoped imported and assigned aliases. Preserve the
explicit `deps.storage` application-port exemption and detect environment reads and
writes. Add negative fixtures for bypasses and positive fixtures for shadowing, pure
operations, lazy code and valid re-exports. Static resolution must not import or execute
target modules.

## Architecture

The [architecture record](architecture.json) covers the existing static helper and its
executable tests. Helpers stay test-only, depend on Python AST/filesystem inspection
and the existing import graph, and never execute inspected application modules.
The parent owns integration, architecture-guide changes and final independent review.

## Task Ledger

- [x] Reproduce missed violations and inspect existing checks.
- [x] Record architecture decisions and validate planning record before implementation.
- [ ] Add regressions and implement scoped target/effect checks.
- [ ] Run architecture/tooling tests, Ruff, typing and import contracts.
- [ ] Document supported static analysis and explicit limitations in parent-owned guide.
- [ ] Reconcile task-owned diff and complete fresh integrated independent review.

## Risks and Limits

Avoid treating function locals as module attributes or leaking aliases between scopes.
Do not infer arbitrary computed attributes, metaclass behavior or reflective imports.
Passing static checks is evidence for covered syntax, not proof of effect freedom.
No dependency versions, application source, installed workflow files or shared services
are in this delegated write scope. Existing pyproject overrides and untracked grid-search
notes are unrelated and preserved.
