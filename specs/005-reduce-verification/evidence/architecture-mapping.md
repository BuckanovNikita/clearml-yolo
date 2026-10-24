# Architecture enforcement mapping — 2026-10-24

The inspected baseline is `9c3f296f370971436afd8cc300c31034d52dd4dc`.
Handwritten rules were removed only after comparing their rejected edges with the
configured import-linter contracts. All 192 formerly forbidden adapter peer pairs
remain rejected; the previous 23 SDK/queue roots remain represented. The new direct
safetensors dependency also has an explicit owner contract.

| Removed duplicate | Retained authority and evidence |
| --- | --- |
| Layer classification and command inventory | Exhaustive root, adapter, application and entrypoint contracts; command independence; console inventory and injected unclassified-module cases |
| SDK owner and exception tables | Actual configured forbidden contracts, including negative ordinary and dynamic SDK edges |
| Adapter peer tables and exceptions | Configured peer contracts; transferred assets inbound/outbound restrictions and exact existing exceptions |
| General inward dependency graph checks | Configured layers, including a transitive helper escape regression |
| Handwritten cycle traversal | Standard-library `TopologicalSorter`, with injected cycles in core, adapters and entrypoints |
| Separate ordinary/dynamic graph policy | Each configured contract receives its own copy of the AST-enriched Grimp graph; stale lazy allowances fail |

The AST-specific checks retain effect ownership, lexical scope and aliases, direct
dependency allowlists for scientific core and pure adapters, inert initializers,
internal SDK reexports, runtime targets and generated Hydra configurations. These
cannot be replaced by import-linter alone. Type-only imports remain included.

Parent integration consolidated duplicated test setup: both inner layers share an
actual-source scan; simple effects join scoped effect cases; eager initializer cases
join definition-time checks; SDK names cross the scoped dynamic-import cases; and
unclassified modules share configured-contract graph injection. Existing assertions
remain represented, with dynamic SDK combinations expanded. A synthetic native-runtime
allowlist assertion was removed because its real boundary is now exercised through
the configured graph contracts, not the unique core/pure-adapter allowlist helper.

Focused integrated result: Ruff and strict mypy passed; architecture tests **256
passed** in **4.83 seconds**. Final ordinary-suite results are recorded separately.
Cancellation assertion migration is mapped in [cancellation coverage](cancellation-coverage.md).

## Final review follow-up consolidation

After review added dependency-inventory regressions, remaining architecture test setup
was consolidated: all 64 distinct lexical source/expectation pairs remain identical
under a read-only AST comparison, nested-class and deferred-binding cases share the
existing effect groups, root-package reexport success/failure join the runtime-target
fixture, and explicit storage aliases join the application port matrix. Both original
storage assertions remain, with core-effect checks extended to every port case.
Initializer scanning uses the same comprehension pattern as inner-layer scanning.
Configured negative graph cases are unchanged. This removes 45 further test lines;
**262 tests passed in 4.82 seconds**, plus Ruff, strict mypy and diff checks.
