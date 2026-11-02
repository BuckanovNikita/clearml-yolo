# Bug assessment: batch worker cleanup permissions

- Date: 2026-11-02
- Slug: batch-cleanup-permissions (generated)
- Source: pasted traceback
- Verdict: valid; high severity, successful estimation can fail during cleanup.

## Observation and cause

The reported older worker_pool.py raises `Independent worker cleanup failed` from
`LinuxProcessTree.running`: `/proc access denied` for PIDs 610671 and 611750.
That launcher is absent in this checkout. Current `runtime/workers.py` still uses
LinuxProcessTree, and its enclosing native scope also enumerates all same-user
processes and reads their environments. Unrelated inaccessible processes poison
cleanup. Actual ownership of the reported remote PIDs cannot be recovered here.

## Remediation and tasks

1. Reproduce with real worker execution and injected unrelated proc denial.
2. Limit live discovery to caller/worker descendants and recorded births. Preserve
   preexisting helper branches, native adoption, PID identity checks and fail-closed
   behavior for inaccessible relevant descendants. Leave historical global recovery intact.
3. Run focused regressions and canonical verification; obtain fresh independent review.
4. Update runtime cleanup guidance and validate documentation. Inspect portable usage
   guidance; this internal fix changes no CLI or recovery procedure.
5. Reconcile owned diff and architecture, then evaluate native release gates.

## Architecture

See [architecture.json](architecture.json). Process and proc effects stay in runtime
adapters. Existing import contracts and negative architecture tests remain authoritative.
Python remains >=3.12.13,<3.14; use existing frozen uv environment and checks.
Pre-existing extensive worktree changes are excluded from this task.

## Current-source assessment amendment

Fetched upstream and inspected commit 73bb044 (version 0.44.7) in an isolated
checkout. It contains the exact reported worker_pool.py, while direct native scopes
already use scoped discovery. Apply marker-filtered scoped discovery to independent
case trees and cooperating training worker trees, anchored at the invocation caller.
Retain per-case markers so cleaning one case cannot signal siblings. Expose the existing
scoped tree and add its owner environment parameter; leave global recovery unchanged.
Conservative failure on inaccessible relevant caller descendants remains deliberate.
The initial old-checkout exploration was backed up and reverted without touching
pre-existing changes. This isolated current-source checkout owns the final patch.

## Release continuation — 2026-11-02

Explicit user authorization covers merging to master and releasing. Reuse the
accepted runtime patch and source checks. The planned next version is 0.44.8;
normal paired source installation tests that version with latest queue 0.1.7.
The repaired stand permits actual CPU/GPU pipeline acceptance, artifact/model
readback and paired current-test comparison. Record closure in [release.md](release.md),
then execute native version/changelog hooks and recheck actual installed metadata
before pushing master and the annotated Git tag. Only root version/changelog
metadata and task-owned prose may change; no dependency resolution changes are committed.
