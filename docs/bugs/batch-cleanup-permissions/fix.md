# Bug fix: batch worker cleanup permissions

- Date: 2026-11-02
- Status: applied and verified; native gate resolved in release follow-up
- Assessment: [assessment.md](assessment.md)

## Changes

Exposed existing `_ScopedProcessTree` as `ScopedProcessTree`, retaining its
identity-validated all-thread traversal and adding the owner environment parameter.
Independent case and cooperating training worker trees now use this scoped discovery
anchored at their invocation caller. Each retains inherited birth/marker filtering,
so case cleanup cannot claim sibling cases. Native scopes and historical global
recovery retain their existing behavior.

Regression tests prohibit whole-proc enumeration while running actual case-pool
completion and training worker cleanup. Existing tests cover overlapping cases,
failed-case peer preservation, detached grandchildren, repeated interruption,
uncertain cleanup retention/retry, helpers, native forks, inaccessible descendants,
thread topology and PID reuse. Updated direct-native test seams to the exposed name.

## Documentation update

Updated the native training worker section of `docs/runtime-isolation.md`.
Inspected portable usage source `corp-skills/skills/clearml-yolo/SKILL.md` and
`references/usage.md` at commit `80ec2a037e008fafe401e39e9f1b507005cb9a0d`.
No portable-source change: CLI, configuration, outputs and recovery instructions
remain the same; implementation now honors invocation ownership without global scans.

## Deviations and limits

Initial inspection used an outdated dirty 0.41 checkout where worker_pool.py was
absent. Fetching upstream identified current 0.44.7 with the exact reported path;
the final fix uses an isolated current-source checkout. Old-checkout exploratory
changes were backed up and reverted, preserving pre-existing changes.

The report's remote host and exact historical PID permissions are unavailable.
Real local subprocess tests prohibit unrelated proc enumeration and reproduce the
failure before the fix. These do not establish CUDA capacity or ClearML publication.
Inaccessible relevant caller descendants remain conservative cleanup blockers;
unknown adopted children must not be ignored merely because provenance is unreadable.

## Final outcome

The regression is resolved by scoped marker-based discovery. Canonical software,
paired queue, documentation and architecture checks passed; see [test.md](test.md).
Required native GPU release evidence is unavailable because the shared Kubernetes
API certificate fails its preflight. Preserve the verified source fix on a dedicated
branch without creating a version tag or pushing an unaccepted release.

## Release follow-up — 2026-11-02

The user requested merge and release; shared-stand repair subsequently unblocked
native verification. [Release acceptance](release.md) records actual successful
CPU/GPU execution and publication/readback. The earlier blocked outcome above
remains historical evidence. No additional runtime fix was required.
