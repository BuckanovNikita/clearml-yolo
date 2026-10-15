# Bug Fix: architecture check blind spots

- **Slug**: architecture-check-blindspots
- **Fixed**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Architecture helpers now resolve complete static runtime targets, inspect definition-time
initializer effects, and track imported/simple assigned effect aliases in lexical scopes.
Negative and positive fixtures verify the original bypasses and preserve valid usage.

## Changes

| File | Change | Contract |
| --- | --- | --- |
| `tests/architecture_helpers.py` | Modified | Resolve every module/class/re-export attribute without executing inspected modules; inspect eager definition expressions; analyze scoped effect aliases and literal dynamic imports |
| `tests/test_architecture.py` | Added regressions | Missing/local attributes fail; valid aliases and re-exports pass; eager effects fail while deferred bodies and shadowed names remain allowed |
| `tests/test_tooling_boundaries.py` | Added helper import contract | Checker imports are limited to the standard library and existing grimp dependency; injected application/SDK imports fail |

Module targets support explicit absolute/relative project imports, root-package re-exports,
simple assignment aliases, nested class attributes and colon-separated attribute paths.
Function locals/nested functions, annotation-only and type-checking-only declarations,
missing attribute segments and cyclic re-exports do not establish runtime targets.

Initializer inspection covers decorator application, defaults, annotations, class bases,
metaclass expressions, class bodies and eager imports inside compound statements. It skips
deferred function/lambda bodies and honors imported `TYPE_CHECKING` aliases and runtime
`else` branches. Scoped effect analysis covers filesystem/network/process calls and
`os.environ` access, with explicit application storage-port exemptions retained.

## Local Verification

The first regression run against unchanged helpers produced **40 failed, 132 passed**,
confirming missed violations and overbroad old behavior. After implementation, the combined
architecture/tooling suite reports **221 passed**. All **43 import contracts** pass.
Scoped Ruff and strict mypy pass; repository Vulture and scoped diff whitespace checks pass.
See [test.md](test.md) for exact commands and remaining acceptance work.

## Deviations from Assessment

The same lexical resolver now supplies literal dynamic-import edges, closing the equivalent
`import_module`/`__import__` alias bypass. Added a helper dependency contract in the existing
related tooling-test file, within delegated ownership; the architecture record was reconciled
and revalidated. The old CUDA-probe comment now describes queue submission, consistent with
the direct-command policy. No production modules, dependency revisions or installed workflow
assets changed in this workstream.

## Task Ledger

- [x] Reproduce failures and validate the initial architecture planning record before fixes.
- [x] Add failing regression fixtures and implement the scoped checks.
- [x] Run focused tests, import contracts, Ruff, mypy, Vulture and whitespace validation.
- [x] Document supported static analysis and limitations in this evidence; send guide wording to parent.
- [ ] Parent: reconcile the architecture guide and run the integrated documentation check.
- [ ] Parent: obtain fresh integrated independent review and validate architecture acceptance.

## Static Analysis Limits

These checks parse source; they never import inspected runtime targets or execute examples.
They do not prove arbitrary reflection, computed import names, `getattr`, generated/metaclass
attributes, inherited attributes, arbitrary wrappers, data-dependent branch reachability or
interprocedural alias flow. Simple alias tracking is not a full Python abstract interpreter;
branch-dependent rebinding and unusual binding syntax require review. Generic filesystem
method checks remain deliberately conservative. Conditional source declarations are inspected,
not executed. No native/GPU/publication claims follow from these tooling tests.

## Independent-review corrections — 2026-10-15

Fresh review reproduced three lexical gaps in the initial implementation:

1. A nested class body incorrectly inherited its outer class namespace. An outer
   class's `os = {}` could hide the module's imported `os.listdir` in an inner class.
   Class headers still evaluate in their definition context; class bodies now exclude
   enclosing class namespaces while retaining enclosing function/module bindings.
2. `def f(): pass; class C: run = f` incorrectly resolved the alias as `C.f`.
   Simple class aliases now resolve previously bound names in their own namespace,
   then module names available when the outer class definition executes. Nested
   classes do not inherit outer-class bindings. Unknown and forward-only aliases
   remain rejected; ordinary method and chained aliases remain supported. Targets
   manufactured by function calls/local factories remain outside static resolution.
3. Deferred bodies missed imports or simple global aliases bound later in module
   initialization, including `def f(): reader('.'); reader = os.listdir`.
   Function/lambda bodies are now inspected after collecting the final enclosing
   bindings. Their defaults, decorators, annotations and class definition expressions
   retain definition-time lookup; function-local shadowing stays authoritative.

Thirty positive/negative fixtures cover these cases. The first 28-case reproduction
run failed 17 cases before correction. After correction and two additional
counterexamples for definition-time behavior, all focused and broader checks pass;
see the appended [verification](test.md#independent-review-correction-verification--2026-10-15).
Only the existing helper/test files and this evidence changed. Production files,
installed-distribution/native evidence and dependency revisions remain unchanged.

The deferred-body model assumes calls occur after enclosing initialization. It does
not interpret calls made during module initialization, arbitrary later rebinding,
branches or complete interprocedural execution. These remain explicit review limits,
not claims that the checker proves all possible runtime effects absent.
