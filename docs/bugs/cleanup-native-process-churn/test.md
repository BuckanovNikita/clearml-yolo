# Bug verification — 2026-11-01

**Result**: original failure mechanism verified fixed; complete release gates pending.

Parent reran the original double-fork exception case: one passed in 2.96 seconds.
The original four task-owned sibling-churn harness now exits zero in 2.263 seconds,
compared with the reproduced 10.144-second timeout before the fix. All harness-owned
workers/supervisors were stopped and waited; unrelated processes were preserved.

```bash
uv run --frozen --no-sync pytest tests/test_direct_descendants.py tests/test_subreaper_process_tree.py tests/test_gpu_cancellation.py tests/test_process_capabilities.py -q
```

Parent result: 64 passed in 45.97 seconds. Scoped Ruff and strict mypy passed for
process_tree.py and both changed test files. Public function/constructor argument
ASTs match the baseline, including the inherited Subreaper constructor. An initial
parent invocation used nonexistent test filenames and exited four without running;
the corrected command above supplies actual verification.

Fresh read-only native_cleanup_safety review returned ship with no actionable
findings. It inspected topology, ownership, PID fences, helper/caller protection,
threaded zombies and tests; it did not rerun tests. Concurrent churn inside protected
helper branches can still delay conservative verification. No claim extends to
unbounded hostile churn or new GPU/live-stand acceptance.

Mutation applicability was reassessed: process_tree is outside the configured core
selection and is not imported by selected tests, conftest's runtime bootstrap or
selected policy modules. Every recorded source/test/fixture/config/lock hash remains
unchanged; the existing fresh 433-mutant evidence remains applicable. Full canonical
and final integrated review are still required by the [ledger](../../../specs/010-cleanup/tasks.md).

## Final integrated acceptance

Canonical receipt 38ae7edf6f434071b262a7cea5027940 accepted the full suite:
4545 passed, 30 skipped and 81 deselected. Fresh integrated review returned ship,
with no actionable findings; see [acceptance](../../../specs/010-cleanup/acceptance.md).
The original regression path is verified. Historical optional/GPU/live-stand limits
remain explicit; Git delivery has its separate required checks in the cleanup ledger.
