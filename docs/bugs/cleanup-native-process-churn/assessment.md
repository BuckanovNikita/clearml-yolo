# Native cleanup depends on unrelated process churn

**Date**: 2026-11-01
**Verdict**: Confirmed runtime cleanup bug; bounded remediation required before release.
**Source**: Local complete-suite failure and task-owned reproduction, no external URL.

## Symptom and reproduction

The final complete suite failed the native double-fork/orphan case with the original
ValueError grouped alongside Owned descendants survived bounded cleanup. Five plain
original-case trials passed; one sibling fork workload delayed otherwise successful
cleanup. Four task-owned sibling workloads reproduced the exact timeout in10.144
seconds. Diagnostics recorded282 scans,245 with no owned live process; final scans
still reported scan_changed. All created supervisors and churn workers were waited
and stopped; unrelated machine processes were never signalled.

## Root cause

_NativeProcessTree inherits machine-wide /proc discovery. Exits of unrelated processes
set scan_changed and unrelated identities enter the two-stable-empty-snapshot barrier.
Cleanup may therefore time out after its actual owned descendants were killed/reaped.
The historical suite failure had no per-scan log; attribution of its exact concurrent
machine activity is inferred, while the same mechanism is now directly reproduced.

## Proposed remediation and architecture

Native live scopes must discover caller descendants and retained identities using
identity-safe per-thread child traversal, reusing existing SubreaperProcessTree
machinery. Keep the generic historical marker/recovery tree's global behavior unchanged.
Preserve helper exclusions, ambiguous adopted-child failure, PID/birth validation,
pidfd operations, subreaper/restoration, threaded living groups and existing deadlines.
No timeout increase, retry, skipped assertion, new dependency or public signature change.

Affected implementation: src/clearml_yolo/adapters/runtime/process_tree.py. Affected
checks: tests/test_direct_descendants.py and existing subreaper/cancellation/capability
checks, with deterministic topology cases using the current fixtures. The adapter
continues to own /proc, signals, child reaping and subreaper effects. No new import
edges, effects in core/application, or ownership exemptions are allowed. See the
[amended architecture](../../../specs/010-cleanup/architecture.json).

## Acceptance

First demonstrate deterministic unrelated-churn/topology failure against current code.
After the minimal change, verify unrelated churn cannot hold an empty native scope;
relevant late forks, inaccessible descendants and unknown helper orphans still block
completion. Cover native/Python forks, all-thread child discovery, live-thread zombie
leaders, PID reuse, protected helpers, interrupts and restoration. Repeat the original
four-sibling stress harness with unchanged ten-second cleanup bounds. Then obtain
focused independent review, repeat affected mutation applicability and full canonical
acceptance, and include the complete change in final independent release review.
