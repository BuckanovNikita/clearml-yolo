# Bug Fix: Ctrl+C leaves GPU processes alive

- **Slug**: ctrl-c-gpu-orphans (resolved from assessment context)
- **Fixed**: 2026-10-13
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied; final review and verification recorded separately.

## Summary

Linux queued supervision now tracks native descendants across detached sessions and
reparenting. Bounded cleanup defers repeated interruption, verifies child exit and
then closes the GPU ticket. Cancellation remains unsuccessful execution.

## Changes

| File | Change |
| --- | --- |
| `src/clearml_yolo/adapters/runtime/process_tree.py` | Stdlib Linux ownership/identity scans, pidfd signalling and nested signal deferral. |
| `src/clearml_yolo/entrypoints/hydra/execution.py` | Unique inherited launch marker; use tracked descendants for termination and exit verification; protect all-job cleanup. |
| `tests/test_gpu_cancellation.py` | Real detached/reparented children, repeated SIGINT with real worker claim/ticket release, unrelated process survival, handler restoration, identity/visibility failures and actual two-rank Torch launcher. |
| `tests/test_gpu_supervision.py` | Adapt attachment-order test to the new private token argument. |
| `README.md`, `docs/runtime-isolation.md`, `specs/022-simple-gpu-wait/contracts/execution.md` | Cancellation behavior, Linux visibility/pidfd requirements and safe existing-ticket handling. |

## Local verification

Both original real-process regressions failed before implementation. The affected
queue/supervision/execution/launcher run passed 79 tests. The expanded cancellation
file passed seven tests, including the installed native Torch launcher with two CPU
ranks. Import-linter kept all 40 contracts; architecture tests passed 94 checks.
Ruff, mypy and Vulture passed. See [test.md](test.md) for final verification and limits.

## Deviations from assessment

The existing supervisor attachment test required a signature update, and README
received a short Russian user instruction; architecture scope was reconciled before
acceptance. No upstream dependency, queue registry or admission policy was changed.
Pre-existing static-analysis/dependency/test edits were preserved.

## Limits and release

The user's other machine was not accessed. Native CPU process evidence does not
establish remote GPU cleanup or ClearML publication. Linux now requires pidfd support
and sufficient /proc visibility; detached native children retain their launch marker.
Windows retains Job Objects; other POSIX systems retain process groups. Killing the
supervisor with SIGKILL cannot run graceful cleanup.

The read-only `scripts.local_release.require_clean(Path.cwd())` preflight returned
exit 1: dirty tracked worktree/index. Existing unrelated modifications prevent release;
no queue files, external processes, commits, tags or pushes were changed by this check.
Full native GPU/ClearML and fresh-distribution release gates are not established here.

## Release continuation

The user subsequently requested release of this fix. See [release.md](release.md)
for isolated scope, native verification and final release evidence. Earlier observations
and deferred-release entries above are retained as historical evidence.
