# Feature Specification: Test quality and GPU controls

**Created**: 2026-10-14
**Status**: Approved for implementation in the user conversation
**Feature context**: `031-test-quality-gpu-controls`; existing checkout retained.

## User Scenarios & Testing

### US1 — Reject unsupported supervision before expensive work (P1)

A user must learn that their interpreter cannot supervise native children before
training starts, rather than lose validation after a successful training stage.
Absent process APIs, unsupported kernel operations and denied capabilities must
produce actionable diagnostics before native work or GPU reservations. Supported
work must complete training, validation, publication and verified cleanup.

### US2 — Manage host GPU capacity explicitly (P1)

Operators list GPUs, disable a physical device across host queues, remove their
own hold, and release an owned stale whole-allocation claim. Integer selectors
match nvidia-smi physical indexes regardless of CUDA visibility; UUIDs are stable
identities. Force release requires a reason and current claim token, refuses
held locks or confirmed live owners, records an audit, and never kills implicitly.

### US3 — Reproduce multi-GPU failures on another machine (P1)

An explicit marked test invocation runs real direct/queued eager/compiled DDP,
retains diagnostics on success and failure, and produces one shareable result
directory. Missing prerequisites fail selected runs. Ordinary tests stay offline.

### US4 — Detect cross-stage correctness defects (P2)

Composed tests and generated inputs protect checkpoint/cache separation, exact
identities, frozen thresholds, evaluation edge cases and queue transitions. Tests
must detect deliberately reintroduced defects rather than only execute code.

## Requirements

- FR-01: Preflight worker, selected job interpreter, guardian and direct native scope before work; no absent pidfd API may first surface after training.
- FR-02: Existing checkpoints, original errors and uncertain-cleanup quarantine remain preserved.
- FR-03: Physical GPU indexes resolve through identity-only NVML enumeration, independent of memory telemetry and CUDA visibility. Store UUIDs, not indexes.
- FR-04: Host-wide per-owner holds survive worker restarts; enable removes only the caller's hold. Recheck holds inside allocation transactions.
- FR-05: Release checks current whole-claim identity and ownership. Force requires an explicit reason, refuses live locks/confirmed owners, audits before removal, and never reports completed work.
- FR-06: An admission fence prevents old workers from ignoring GPU controls. Existing live allocations can finish safely.
- FR-07: Marked multi-GPU tests verify real ranks/devices, training, validation, prediction, checkpoint reload, required publication and cancellation/failure cleanup.
- FR-08: Remote instructions select only those tests and retain machine, source, configuration, rank, queue and task evidence without credentials.
- FR-09: Offline composed/property tests cover identity, serialization, evaluation and stateful queue invariants; deliberate semantic faults demonstrate sensitivity.
- FR-10: Hypothesis/pytest-cov are development-only; approved external sources and existing runtime versions remain unchanged.

## Success Criteria

- Every unsupported-capability fixture rejects before a workload or GPU claim exists.
- Index and UUID selectors target the same card under reordered, restricted and empty CUDA visibility.
- Cross-root holds and complete-claim release remain correct under competing operations and interrupted writes.
- Remote runs either establish their requested native behavior or return retained failing evidence; unsupported hardware is not a passing result.
- Each selected deliberate defect is caught by its intended assertion.

## Assumptions and boundaries

Linux/WSL is the queue target. Existing CPU DDP tests are retained. Physical
multi-GPU acceptance awaits user-supplied remote results and is never inferred
from mocked, CPU or single-GPU checks. ClearML uses normal SDK configuration.
Runtime fixes are limited to supervision preflight and approved GPU controls.
The existing CUDA-logical semantics of queue submission are not changed.
