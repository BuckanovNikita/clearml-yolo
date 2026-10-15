# Bug Fix: Queue job finalization and inference handoff

- **Slug**: queue-job-finalization (reused from assessment context)
- **Fixed**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Status**: released as 0.30.2; portable guidance released as 0.2.4

## Changes

The ordinary job now receives only an inherited lifecycle socket. Its resources
port frees training memory before reporting training completion and waiting for a
bounded acknowledgement. The supervisor retains the first ordered GPU and frees
other queue reservations. Jobs neither import queue management nor scan host
processes when supervised. Direct invocation cancellation is unchanged.

The guardian uses its dedicated subreaper topology, including all native threads,
recorded birth identities and adopted children. It never scans unrelated process
environments. Inaccessible relevant topology still blocks release. Recovery after
supervisor death retains the existing conservative global marker discovery.

Shrinking a lease durably removes extra claim files while the retained claim still
quarantines the complete original allocation. The retained record is then atomically
replaced with the reduced claim before extra locks are released. Failure before
commit retains full quarantine; failure after commit retains at least the first
GPU claim and cannot acknowledge an incomplete handoff. Existing claim tokens
change with the reduced allocation.

## Files and ownership

- Runtime: `process_tree.py`, new `execution_lifecycle.py`.
- Queue: `guardian.py`, `locks.py`, `exec_child.py`.
- Composition: `entrypoints/composition.py`, `entrypoints/hydra/common.py`.
- New regressions: `test_execution_lifecycle.py`, `test_queue_handoff.py`,
  `test_subreaper_process_tree.py`.
- Maintained docs: queue/runtime contract, project summary, Russian README, current
  queue specification and project-owned end-to-end skill/prerequisites.
- Companion portable usage/evaluation references in corp-skills; source installation
  is separate and not performed.

## Local verification

Before changing the command boundary, the completed-artifact regression failed
with the original `UnverifiableProcessTreeError` raised from native scope exit.
After correction, lifecycle and direct execution checks passed (45 tests), then
seven lifecycle checks passed with the bounded-timeout case added. New guardian
handoff cases passed (15); combined guardian/grace/process checks passed (33).
New subreaper cases passed (13), including a regression that first demonstrated
premature release for a zombie leader with living threads; combined process checks
passed (64). These are overlapping selections, not additive test counts.

Parent full Ruff, strict mypy (322 files), Vulture and 43 import contracts passed.
Final routine/native/distribution/documentation outcomes belong in [test.md](test.md).

## Deviations from assessment

The user explicitly clarified both queue launch and release of extra reservations
for concurrent jobs. These requirements were captured before implementation.
Documentation scope additionally includes the project-owned end-to-end skill and
its prerequisite reference because they stated the superseded whole-pipeline hold.
No installed Spec Kit tooling, dependency source or revision changed.

## Task progress

- [x] Architecture plan validated before implementation.
- [x] Completed-artifact failure reproduced before correction.
- [x] Job boundary, scoped supervisor and durable handoff implemented.
- [x] Focused regression and static/import checks pass.
- [x] Documentation updated; Markdown/link/portable metadata checks pass.
- [x] Final routine, real CPU/single-GPU, distribution and architecture checks.
- [x] Fresh independent review and diff reconciliation.
- [x] Native Git-tag-only release and verified delivery; see [release.md](release.md).
