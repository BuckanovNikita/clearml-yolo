# Implementation Plan: direct execution and shared cy-queue

## Current status amendment — 2026-10-15

The original plan below records implementation intent at its date. Allocation
contraction is now required after native training and memory release; only acknowledged
handoff permits inference. Current-generation reservations, explicit holds and fresh
memory admission govern capacity; stale unlocked records retain recovery evidence
without automatically blocking admission. See the [current contract](contracts/queue.md)
and [status map](../../docs/implementation-status.md). Completed tasks remain unchanged.

## Summary

Implement [spec.md](spec.md) using the existing Python 3.12/uv layered package.
Direct Hydra commands keep native settings and sequential BasicLauncher. Queue entrypoints
compose immutable snapshots and inject queue storage/inventory/process adapters into a
queue application service. NFS holds atomic durable manifests/events; host-local locks
and quarantine records coordinate UUID capacity across roots. Guardians are separate
same-user subreapers, never ClearML owners. Textual is an optional UI import only.

## Technical Context

Reuse NVML inventory, LinuxProcessTree pidfd/start-time/marker protections, existing
native DDP relay and single-task lifecycle. No SDK path rewriting or dependency-source
updates. Keep original native/compiler exceptions. Admission thresholds do not predict
compiled memory capacity; allocation contraction is deferred.

## Constitution Check

Typed boundaries, inward imports, effect ownership, strict config, native model ownership,
publication barriers, test evidence and preservation requirements remain in force.
The explicit approved plan supersedes historical Principle III prohibitions on persistent
workers, GPU count requests and reorder operations, and the old launcher requirement.
Record that intended contract change here; do not modify installed workflow tooling or
historical completed specifications. No approvals remain outstanding for implementation.

## Architecture

The executable planning/acceptance index is [architecture.json](architecture.json).

| Module | Interface and effects |
| --- | --- |
| core.queue | Frozen request/job/order/allocation records, pure earliest-runnable decisions; no I/O or SDK/Hydra types |
| application.queue | Queue service and explicit storage/inventory/process ports; no concrete adapters or filesystem/process effects |
| adapters.queue | Atomic NFS storage, UID validation, local locks/quarantine, NVML and guardian supervision; no model/ClearML/Hydra SDKs |
| entrypoints.queue / entrypoints.hydra.queue_config / entrypoints.queue_tui | Compose snapshots, bind native settings, CLI actions, lazy Textual UI, compatibility verification |
| entrypoints.hydra.common / runtime bootstrap / storage filesystem | Direct pipeline and project write containment; no scheduling imports or Textual |
| observability / clearml / native integration / prediction backends | FD capture, aggregate progress, bounded console publication, owner-only metrics/lifecycle and quiet prediction; no queue dependencies |

Retain LinuxProcessTree as generic process ownership adapter. Direct native cleanup calls
native-runtime memory release without queue phase contraction. All new SDK/import/dynamic
launch edges need exact architecture coverage and negative tests.

## Existing changes

Preserve uncommitted process_tree.py, execution.py cancellation integration, cancellation
and supervision tests, README/runtime-isolation/022 contract amendments, bug records,
and exact local tool.uv.sources section. Reconcile retained cancellation behavior into
guardian tests before retiring obsolete scheduler. Completed feature 026/v0.26.1 stays done.

## Dependency-aware workstreams

1. Parent: specification, architecture gate, baseline coordination, direct/config/path split.
2. Queue implementer: core.queue, application.queue, adapters.queue and dedicated tests;
   starts after shared request/service interfaces and architecture validation.
3. Observability implementer: capture/publisher/progress and native adapters/tests;
   starts after explicit paths and sole lifecycle owner decisions.
4. Native investigator: isolated existing baseline and SIGILL investigation; no production writes.
5. Parent: CLI/TUI + Hydra snapshots after queue service API is fixed; integration/import
   contracts, complete checks, documentation and installed distribution acceptance.
6. Fresh independent read-only review after parent verification, then architecture acceptance
   and established Git-tag-only release if all required gates pass.

Queue/observability/native work has exclusive file ownership. Parent owns pyproject/lock,
architecture helpers, direct entrypoints, docs and final integration. Review and release
are sequential dependencies; unavailable multi-host/multi-user/physical GPU evidence stays open.

## Verification and documentation

Run full pytest, Ruff, mypy, Vulture, import-linter, architecture negative cases,
Markdown/local links/examples and fresh wheel/sdist installed checks. Verify native
single/five-GPU direct/queued eager/compiled parity, actual two-user/two-host NFS behavior,
live remote console/scalars, physical cancellation, guardian death and filesystem writes.
Update README (Russian), project/current contracts, filesystem/runtime/diagnostics/development
and affected generated examples. Preserve historical evidence; append reconciliation notes.
