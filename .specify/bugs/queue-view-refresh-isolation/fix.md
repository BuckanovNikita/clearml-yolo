# Bug Fix: Queue view refresh isolation

- **Slug**: queue-view-refresh-isolation (explicit user plan)
- **Fixed**: 2026-10-19
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Queue listing refreshes each owned job's private telemetry independently. An unreadable
snapshot or status leaves that job's recorded public summary visible with a transient
safe warning, while healthy jobs continue updating. Worker refresh remains strict.

## Changes

| Scope | Change |
| --- | --- |
| Core queue | Typed QueueRefreshIssue and default-empty QueueView.refresh_issues |
| Application queue | Explicit monitoring port, affected-summary preservation, visibility filtering |
| Queue storage | PrivateSnapshotError classifies only private reads/validation; shared transaction and authorization errors propagate |
| Queue runtime | Monitoring performs telemetry reads/publication only; strict refresh still owns lifecycle reconciliation |
| CLI/presentation/TUI | Warning counts and per-row messages; JSON diagnostics with readable references |
| Regression tests | Mixed faults/states, repaired warnings, healthy progress, reservation/outcome preservation, strict execution, legacy config, CLI and headless TUI |

## Architecture

[architecture.json](architecture.json) records module ownership and existing executable
contracts. No import direction, dependencies, durable formats, task migration or GPU
reservation policy changed. Monitoring deliberately does not call lifecycle reconciliation.
Publication errors remain outside the per-job read catch boundary.

## Local verification

The original missing-snapshot test failed before implementation with FileNotFoundError
from QueueService.list → refresh → load_snapshot. After the fix, the initial focused
service/storage set passed (18 tests); the expanded isolation set passed (28 tests).
Rendering tests first failed for missing diagnostics, then 40 rendering/readability tests
passed. Final integrated checks and documentation evidence are recorded in [test.md](test.md).

## Documentation and deviations

Update queue guide, shared queue contract and companion portable usage/evaluation references.
README and the current contract index already route to the guide; no navigation changes
are needed. The exact historical ValueError remains unverified; the reproduced missing
snapshot failure and expected private read/validation classes define this fix's scope.
Storage was included to distinguish private-read failures from queue-wide transaction errors;
catching all RuntimeError around load_snapshot would incorrectly hide coordination failures.

## Preservation and release

Unrelated existing ClearML/cache code, docs, architecture tests, changelog and local source
overrides remain outside the task-owned diff. Use an isolated release checkout for native
hooks/versioning so those edits are neither stashed nor included. No live shared queue,
ClearML service, GPU workload or installed skill is modified.
