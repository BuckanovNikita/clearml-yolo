# Cancellation coverage reconciliation — 2026-10-24

Removing the unused `adapters.runtime.supervision` API also removes its exclusive
Windows/process-group wrapper tests. Meaningful Linux ownership scenarios use the
active `process_tree` API and queue callers. Four migrated tests duplicated stronger
retained caller coverage; removing them reduces maintained Python by 210 lines.
No production process-tree or queue behavior changed.

## Removed duplicates and retained assertions

The removed functions were in `tests/test_gpu_cancellation.py`. Queue references
below are in the compatible queue checkout's `tests/test_shared_queue_processes.py`.

| Removed test | Retained coverage and assertion mapping |
| --- | --- |
| `test_repeated_ctrl_c_finishes_worker_cleanup` | CY [`test_repeated_interrupts_preserve_original_error_until_fork_cleanup`](../../../tests/test_direct_descendants.py) sends repeated SIGINT/SIGTERM, requires exact exit 130 and completion marker, and checks the owned child was reaped. Queue `test_repeated_guardian_signals_hold_capacity_until_ignoring_child_is_reaped` additionally requires retained capacity during cleanup and cancelled state with no live child afterward. |
| `test_reused_pid_is_not_signalled` | Queue `test_recovery_reuses_persisted_birth_and_never_signals_replacement_pid` uses real process identity and the pidfd path, requires the replacement process survive SIGKILL selection, retains the persisted birth and reports no owned running process. CY [`test_live_scope_does_not_adopt_known_pid_replacement`](../../../tests/test_subreaper_process_tree.py) refuses even opening a recycled target. The distinct post-snapshot parent/session race remains in `test_gpu_cancellation.py`. |
| `test_release_retries_transient_denial_until_fresh_verified_scan` | Queue `test_cleanup_waits_for_fresh_verification_after_transient_unreadable_candidate` calls the real guardian cleanup boundary with temporary Linux process-access denial, requires successful root cleanup and preserves the unknown process. CY retains permanent-unreadability rejection, preventing an early successful result from replacing verified cleanup. |
| `test_cancellation_kills_detached_rank_and_preserves_unrelated_process` | Queue `test_direct_scope_reaps_detached_rank_after_repeated_interrupt_and_preserves_existing_child` requires detached-rank cleanup and unrelated-child survival. Queue `test_guardian_cancellation_reaps_subreaper_children` and CY [`test_live_scope_cleans_fork_session_adoption_and_thread_children[orphan]`](../../../tests/test_subreaper_process_tree.py) require cleanup/reaping after the root exits first. Queue guardian-death recovery and retained CY native-torchrun cancellation exercise marker-based historical ownership and detached native ranks. |

## Distinct coverage retained

[`test_gpu_cancellation.py`](../../../tests/test_gpu_cancellation.py) retains nested
deferred interruptions and exact handler restoration, inaccessible owned identity,
real Torch distributed rank cancellation, permanent unknown-process access denial,
environment-denial liveness rechecks, PID reuse after snapshots, late-fork discovery
and disappearing-enumeration races. These exercise distinct marker/recovery paths;
they were not removed based merely on similar test names.

[`test_direct_descendants.py`](../../../tests/test_direct_descendants.py) retains
Python/native forks, orphan adoption, existing helper protection, ambiguous ownership,
original exception preservation and resource restoration. The live subreaper tests
retain thread topology, root-exit adoption and local discovery without unrelated
process scans. [`test_process_capabilities.py`](../../../tests/test_process_capabilities.py)
still validates preflight; it supplies no substitute for cancellation assertions.

## Executed checks

Before deduplication, the migrated CY cancellation/direct/subreaper selection passed
45 tests in 52.67 seconds; the complete queue caller file passed 15 in 12.25 seconds.
Both run real task-owned Linux processes and clean up their fixtures. They establish
process ownership behavior, not GPU admission hardware or ClearML publication.

After deduplication, the CY selection passed 40 tests in 44.62 seconds and the queue
caller file passed 15 tests in 11.92 seconds. Focused Ruff and strict mypy passed for
the changed cancellation test file. This document passed Markdown/local-link
validation with no issues.

```bash
uv run --frozen --no-sync pytest -q tests/test_gpu_cancellation.py tests/test_direct_descendants.py tests/test_subreaper_process_tree.py
uv run --frozen --no-sync ruff check tests/test_gpu_cancellation.py
uv run --frozen --no-sync mypy tests/test_gpu_cancellation.py
```

From the compatible queue checkout, using CY's prepared environment:

```bash
uv run --frozen --no-sync --project ../clearml-yolo pytest -q tests/test_shared_queue_processes.py
```

The parent acceptance stage owns the canonical ordinary suite, documentation
validation, independent review and final architecture reconciliation.

## Final helper consolidation — 2026-10-24

Cancellation, direct-descendant and subreaper tests share nonempty-file readiness
polling; existing callers retain their eight-second default and cancellation passes
its original ten-second deadline. Liveness assertions share an independent raw
`/proc` reader rather than production identity lookup. Duplicate local imports are
consolidated. No tests or assertions were removed in this follow-up, which removes
33 further Python lines. Ruff, strict mypy and diff checks passed; the three-file
subprocess suite passed **40 tests in 46.05 seconds**.
