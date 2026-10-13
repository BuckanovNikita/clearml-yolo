# Bug Verification: Ctrl+C leaves GPU processes alive

- **Slug**: ctrl-c-gpu-orphans (resolved from fix context)
- **Tested**: 2026-10-13
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified for the reproduced CPU process lifecycle defects; remote GPU and release acceptance remain unverified.

## Checks performed

All commands ran from the repository using the existing locked environment with
`uv run --frozen --no-sync`; no dependency synchronization or update was performed.

| Check | Command / action | Result |
| --- | --- | --- |
| Original failures | Two real subprocess regressions before implementation | Both failed at the intended surviving-child/worker assertions. |
| Baseline | `pytest tests/test_gpu_supervision.py tests/test_gpu_queue.py tests/test_hydra_queue_launcher.py -q` | 57 passed before implementation. |
| Affected behavior | `pytest tests/test_gpu_cancellation.py tests/test_gpu_supervision.py tests/test_gpu_queue.py tests/test_gpu_execution.py tests/test_hydra_queue_launcher.py -q` | 79 passed after implementation; no failures. |
| Final cancellation coverage | `pytest tests/test_gpu_cancellation.py -q` | 8 passed, including native Torch two-rank CPU launch, orphaned ranks, real repeated SIGINT, actual queue claim/release, unrelated processes and visibility/identity checks. |
| Final portability amendment | `pytest tests/test_gpu_cancellation.py::test_unreadable_new_process_blocks_verification_without_being_killed -q` | 1 passed; privileged runners may skip when they can inspect the control process. |
| Full regression | `pytest -q` | 2269 passed, 30 skipped, 56 warnings; exit 0. Includes native CPU distributed training regression tests. |
| Imports | `lint-imports` | 40 contracts kept, none broken; exit 0. |
| Architecture | `pytest tests/test_architecture.py -q` | 94 passed, including injected forbidden-edge/cycle rejection; exit 0. |
| Lint | `ruff check .` | Passed; final changed test also checked after portability amendment. |
| Types | `mypy .` | Success, 285 source files; exit 0. |
| Dead code | `vulture` | Passed, exit 0. |
| Documentation | `git diff --check` and inline Python Markdown/local-link validation | Passed; final artifact validation recorded below. |
| Independent review | [review.md](review.md) | Ship after documented visibility limitation and regression. |
| Release preflight | `scripts.local_release.require_clean(Path.cwd())` | Blocked, exit 1: dirty tracked worktree/index. |

The full suite collected before the last two cancellation scenarios were added;
the final eight-test file was run separately afterward. The final portability change
only added a capability-based skip and was verified with its affected test and Ruff.
Warnings were dependency deprecations/scientific fixture warnings, not hidden failures.
Skipped checks are not reported as passes.

## Documentation and architecture acceptance

Updated README cancellation instructions, the runtime isolation guide and the
maintained GPU execution contract. The new runtime module uses only the standard
library; Hydra owns subprocess launch and lease ordering. Existing import/architecture
contracts cover the module and were not weakened. [architecture.json](architecture.json)
records checks, review and complete task-owned diff reconciliation. Documentation
validation checks UTF-8, terminal newlines, balanced fenced blocks, trailing whitespace
and every Markdown local-link target in the changed docs and bug artifacts. No new
shell/configuration example was introduced.

## Remaining limits and completion ledger

- [x] Reproduce both defects before implementation and verify their corrected paths.
- [x] Validate architecture planning, implementation, behavior and dependency checks.
- [x] Update/validate documentation and obtain independent review.
- [x] Preserve unrelated edits and terminate task-owned reproduction/test processes.
- [ ] Commit/release: deferred by unrelated dirty worktree; regular commit hooks would
  automatically stash unstaged edits, which project instructions prohibit. No hook
  was bypassed and no work was stashed, reset or reverted.
- [ ] Full GPU/ClearML and fresh-distribution release gates: not run; no release claim.

The original multi-GPU host was not accessed. CPU processes and real native Torch
launch establish lifecycle cleanup, not remote CUDA/NCCL, memory release or uploads.
Linux requires pidfds, inherited ownership markers and process visibility; a newer
same-user opaque process can prevent verified cleanup. Windows Job Objects are
unchanged. Forced supervisor death cannot run these graceful cleanup handlers.
No pre-existing GPU processes or shared services were stopped; no queue registry was
manually edited or deleted. Existing remote orphans require cleanup on their own host.

## Release continuation

The user subsequently requested release of this fix. See [release.md](release.md)
for isolated scope, native verification and final release evidence. Earlier observations
and deferred-release entries above are retained as historical evidence.

## Feature 029 integration — 2026-10-13

The records above preserve the preceding cleanup implementation and checks. Feature
[029](../../../specs/029-shared-cy-queue/spec.md) replaces the old Hydra scheduler.
Its generic process-tree ownership and signal protections are retained in runtime
`process_tree.py`/`supervision.py` and extended by queue guardians and direct native
descendant scopes. The new [task ledger](../../../specs/029-shared-cy-queue/tasks.md)
owns integrated verification, physical GPU cancellation, forced worker/guardian death,
reservation recovery and release acceptance. Earlier counts are historical evidence,
not a claim that the refactored execution paths have passed those same checks.

Feature 029 now records actual one-GPU repeated direct interruption, owner-first
queue cancellation, worker/guardian forced termination, reservation retention and
verified recovery in its [native evidence](../../../specs/029-shared-cy-queue/native-verification-2026-10-13.md).
Corrected normal queue cancellation published the original signal diagnostic before
capacity release; exact recorded owned processes and GPU claims were absent after
cleanup. This extends the historical CPU evidence above without changing its result.
Physical multi-GPU/DDP and actual multi-user/multi-host NFS acceptance remain open
in feature 029; the original cuBLAS and intermittent SIGILL causes remain unresolved.
