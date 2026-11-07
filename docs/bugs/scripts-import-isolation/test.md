# Bug verification: package-weights tests depend on test order

- Date: 2026-11-07
- Assessment: [assessment.md](assessment.md); fix: [fix.md](fix.md); review:
  [shared review](../estimate-error-diagnostics/review.md)
- Result: **verified**

## Original failure path

```bash
env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest -q -p no:randomly -p no:testmon tests/test_package_weights.py
```

- Before: `ModuleNotFoundError: No module named 'scripts'`, 1 error during collection.
  The same file passed after `tests/test_check_docs.py` (62 passed).
- After: `14 passed`.

## Regression

`tests/test_tooling_boundaries.py::test_script_importing_test_module_collects_in_a_fresh_session`
is parametrized over `test_check_docs.py`, `test_local_release.py`,
`test_package_weights.py` and `test_severstal.py`.

- First draft with plain `python -m pytest`: all four passed before the fix, because
  `-m` prepends the working directory. That draft could not detect the defect.
- With `python -P -m pytest`, which matches the console script: before the fix the
  `test_package_weights.py` case failed (`No module named 'scripts'`, 1 failed,
  4 passed); after the fix all passed.

### Fail-first against origin/master (2026-11-07)

In a scratch worktree at `origin/master` `fe7332b`, the fixed `test_package_weights.py`
passes on its own, because the fix is inside that test file. So the fail-first check
kept master's `tests/test_package_weights.py` and copied only the new
`tests/test_tooling_boundaries.py`:

- `pytest ... tests/test_tooling_boundaries.py -k "fresh_session or inventory_covers"`:
  `1 failed, 4 passed`; the failure was `[tests/test_package_weights.py]`, where the
  `-P` collection subprocess exited 2 with `1 error during collection`.
- `pytest ... tests/test_package_weights.py`:
  `ModuleNotFoundError: No module named 'scripts'`, 1 error.

The pre-commit full suite passed (4840 passed). Post-rebase full-suite results are in the
[shared verification](../estimate-error-diagnostics/test.md#checks).
