# Bug verification: batch-estimate error diagnostics drop telemetry evidence

- Date: 2026-11-07
- Assessment: [assessment.md](assessment.md); fix: [fix.md](fix.md); review: [review.md](review.md)
- Result: **verified** for the CPU-reproducible failure path. Native selected-L is
  not re-run (see limits).

## Reproduction before and after the fix

The original failure path is constructed on CPU: a `run_workers` exception group,
lone query failures and a fake `nvidia-smi` that prints NVML text and exits 12. It
runs through the real `NativeBatchProbe.run`, `monitor_devices`, `gpu_states`,
`_query` and `estimate_batches` code.

Command for both runs (worktree, before and after the source change):

```bash
env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest -q -p no:randomly -p no:testmon \
  tests/test_gpu_inventory.py tests/test_batch_probe.py tests/test_batch_estimate_workflow.py tests/test_tooling_boundaries.py \
  -k "nvml or partial_output or empty_streams or error_trials or classification_is_unchanged or still_propagates or reaches_the_trial or grouped or error_diagnostic or fresh_session or inventory_covers"
```

Before the fix: `13 failed, 10 passed`. Failures:

- the gpu_inventory notes tests: `'CalledProcessError' object has no attribute '__notes__'`;
- all three probe `error_trials` cases and `reaches_the_trial_diagnostic`: the
  `ExceptionGroup`, `CalledProcessError` or `TimeoutExpired` escaped `run()`;
- the case diagnostic: it was `'ExceptionGroup: Worker execution and cleanup failed (2 sub-exceptions)'`;
- the formatter tests: `error_diagnostic` was absent.

The 10 that passed were pinning tests for existing behavior:

- the `RuntimeError` "GPU" to `contaminated` / `error` mapping (3 cases);
- `KeyboardInterrupt` group propagation;
- no notes when the failed query's streams are empty;
- the scripts-import tests, apart from the `-P` correction recorded in the
  [isolation bug](../scripts-import-isolation/test.md).

After the fix: `23 passed` (same selection, including the corrected isolation tests).

## Checks

| Check | Command | Result |
| --- | --- | --- |
| Full suite | `env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest --testmon-noselect -q -p no:randomly` | pass: 4840 passed, 30 skipped, 81 deselected, exit 0 (23 min 40 s); includes architecture negative cases and CPU-DDP |
| Ruff | `uv run --frozen --no-sync ruff check .` | pass |
| mypy (strict) | `uv run --frozen --no-sync mypy .` | pass, 465 files |
| Vulture | `uv run --frozen --no-sync vulture` | pass |
| import-linter | `uv run --frozen --no-sync lint-imports` | pass, 52 kept, 0 broken |
| Documentation | `uv run --frozen --no-sync python scripts/check_docs.py --all` | pass, 0 issues |
| Mutation | `[tool.mutmut] only_mutate` excludes all changed modules | not applicable |

Commit hooks and the paired CY/queue release check are recorded in the release
section below once run.

## Limits

CPU only, with `CUDA_VISIBLE_DEVICES` empty: no GPU, no native selected-L trial and
no ClearML stand. The nvidia-smi failure is simulated by an executable that
reproduces the observed exit status and NVML message; the WSL driver outage itself
is not reproduced. Selected-L remains blocked on the environmental decision in the
[source assessment](../selected-l-telemetry-loss/assessment.md#impact-on-wp1).
