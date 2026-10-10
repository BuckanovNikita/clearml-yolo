# Implementation plan

## Architecture and interface

Implement `adapters.observability.tracing.trace_operation(name, *, context=None)` as
a context manager usable also as a decorator. Add the same typed context-manager
capability to `ExecutionResources` and composition. Application code uses this port;
adapters use the helper directly. `trace_command(name)` owns command lifecycle and
emits `command.return` after cleanup. `trace_task(task_id)` binds task correlation.
No external SDK imports, sink changes or threads at import time.

One monitor samples immutable per-thread operation snapshots without application locks.
Register operations before emitting START, so a blocked sink remains observable.
Monotonic clocks measure intervals/durations. Render only bounded safe scalar context;
stack frames contain filename/function/line only. Failures in diagnostics are isolated.

## Dependency-aware parallel waves

Parent owns observability, ports/composition, architecture policy, shared fixtures,
cross-area tests, Spec Kit records and integration. Maximum parent plus three agents;
agents do not delegate. Shared interfaces freeze before parallel source edits.

| Wave | Parent | Independent assignments | Acceptance/dependency |
| --- | --- | --- | --- |
| 0 | Standing instructions, spec/plan/tasks, helper/port/watchdog tests | Read-only A publication, B runtime/storage, C workflow/evaluation inventories | Foundation tests and API freeze |
| 1 | Workflows, command lifecycle, shared tests | A ClearML; B FiftyOne; C GPU/native/DDP, each with dedicated tests | Frozen API; focused passing tests and coverage evidence |
| 2 | Cross-component/subprocess verification and integration | A storage/cache/export; B evaluation/reporting/YOLO; C maintained docs/README | Wave 1; every boundary covered or excluded with reason |
| 3 | Combined-diff inspection and full gates | Fresh read-only independent reviewer | Parent checks; ship verdict after fixes |

Sequential dependencies: foundation before instrumentation; combined checks before final
review; review before release. Reuse inventory agents for implementation where useful.
Read-only inventories requested GPT-6.1 Sol medium in fresh contexts. Runtime settings
are not independently observable.

## Verification and documentation

Use focused pytest first, then full pytest including native CPU DDP, Ruff, strict mypy,
lint-imports, all command helps/config generation and repository hooks. Native execution
follows the project end-to-end/environment skills and records dated evidence. Synthetic
waits do not prove the original remote hang resolved.

Update README.md (Russian), docs/project-contracts.md, docs/current-contracts.md,
docs/python-import-migration.md if needed, and a maintained diagnostics guide. Validate
Markdown, local links and Bash examples. Record all evidence and coverage in this feature.
Keep `.specify/` and installed workflow tools unchanged per project policy; use explicit
feature path for workflow operations. No dependency revisions change.
