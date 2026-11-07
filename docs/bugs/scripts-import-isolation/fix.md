# Bug fix: package-weights tests depend on test order

- Date: 2026-11-07
- Status: applied
- Assessment: [assessment.md](assessment.md)

## Changes

| File | Change |
| --- | --- |
| `tests/test_package_weights.py` | Imports `scripts.package_weights` inside a module-level `pytest.MonkeyPatch.context()` with `syspath_prepend(str(ROOT))`, matching `tests/test_check_docs.py` and `tests/test_severstal.py`. `sys.path` is restored after import. |
| `tests/test_tooling_boundaries.py` | Finds every `tests/test_*.py` module that imports `scripts` (AST) and collects each one alone in a fresh `python -P -m pytest --collect-only` subprocess. `-P` matches the pytest console script, which does not prepend the working directory; plain `python -m` would hide the defect. A guard asserts that the inventory includes the known modules. |

## Deviations from assessment

None.

## Documentation update

No documentation change. Inspected `docs/development.md` (Verification) and the
test-tooling guidance: no documented command, contract or example changes. The fix
restores the documented ability to run a single test module.
