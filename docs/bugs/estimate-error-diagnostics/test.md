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

### Fail-first against origin/master (2026-11-07)

A scratch detached worktree at `origin/master` `fe7332b` (external dependencies
copied, `uv sync --frozen`) received only the five changed test files
(`tests/test_batch_estimate_workflow.py`, `tests/test_batch_probe.py`,
`tests/test_gpu_inventory.py`, `tests/test_package_weights.py`,
`tests/test_tooling_boundaries.py`) and ran them whole:

```bash
env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest -q -p no:randomly -p no:testmon <the five files>
```

Result on unfixed source: `13 failed, 169 passed`. The failures:

- the six `error_diagnostic` and case/preparation diagnostic test cases in
  `test_batch_estimate_workflow.py` (four functions, the formatter test parametrized
  three times);
- the three `error_trials` cases (`cleanup-group`, `lone-query-failure`,
  `lone-query-timeout`) and `test_failing_nvidia_smi_output_reaches_the_trial_diagnostic`
  in `test_batch_probe.py`;
- the three notes tests in `test_gpu_inventory.py`
  (`'CalledProcessError'`/`'TimeoutExpired' object has no attribute '__notes__'`).

The scratch worktree was then removed. In this worktree, the same five files gave
`182 passed` before the commit.

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

## Commit and post-rebase verification (2026-11-07)

- Commit hooks: the first attempt, with CUDA visible, failed in the affected-pytest
  hook. Exit 134 came from `Fatal Python error: Aborted` in `torch.cuda._lazy_init`
  (`tests/test_torchvision_distributed.py`). At that time `nvidia-smi -L` itself
  crashed with `*** stack smashing detected ***`, the host GPU driver fault this bug
  family concerns. The commit was retried with `CUDA_VISIBLE_DEVICES=` and no hook
  skipped. All hooks passed (Ruff, mypy, Vulture, import contracts, affected pytest,
  Markdown/links, changelog, local semantic version: no tag on a branch).
- Rebased onto `origin/master` `fe7332b` without conflicts. The generated
  `CHANGELOG.md` hunk became empty because upstream already has that entry.
- Full suite after rebase
  (`env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest --testmon-noselect -q -p no:randomly`),
  run 1: `1 failed, 4839 passed, 30 skipped, 81 deselected` (20 min 50 s). The failure
  was `tests/test_clearml_session.py::test_console_streams_reach_offline_sdk_without_duplicates`,
  where the offline ClearML subprocess printed `*** stack smashing detected ***` and
  hung until the 60 s timeout. The test passed when run alone (`1 passed`). No changed
  module is imported by `adapters/clearml` or `adapters/observability`. Classified as
  the concurrent host driver fault, not this change.
- Full suite run 2, same command and tree: pass, `4840 passed, 30 skipped,
  81 deselected`, exit 0 (19 min 6 s).

The paired CY/queue release check is not part of this step; the branch is not pushed.

## Limits

CPU only, with `CUDA_VISIBLE_DEVICES` empty: no GPU, no native selected-L trial and
no ClearML stand. The nvidia-smi failure is simulated by an executable that
reproduces the observed exit status and NVML message; the WSL driver outage itself
is not reproduced. Selected-L remains blocked on the environmental decision in the
[source assessment](../selected-l-telemetry-loss/assessment.md#impact-on-wp1).
