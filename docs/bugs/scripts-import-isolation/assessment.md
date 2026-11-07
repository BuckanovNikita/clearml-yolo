# Bug assessment: package-weights tests depend on test order

- Date: 2026-11-07
- Slug: `scripts-import-isolation` (generated)
- Source: observed by the parent agent; reproduced here (pasted description, no URL).
- Verdict: valid; low severity. This is test isolation only; no application behavior
  is affected.

## Symptom

`pytest tests/test_package_weights.py` alone fails during collection with
`ModuleNotFoundError: No module named 'scripts'`. In the full alphabetical run it passes
because `tests/test_check_docs.py` is collected first and leaves `scripts` in
`sys.modules`.

## Reproduction

```bash
env -u PYTEST_ADDOPTS uv run --frozen --no-sync pytest -q -p no:randomly -p no:testmon tests/test_package_weights.py
# ERROR tests/test_package_weights.py ... ModuleNotFoundError: No module named 'scripts'
env -u PYTEST_ADDOPTS uv run --frozen --no-sync pytest -q -p no:randomly -p no:testmon tests/test_check_docs.py tests/test_package_weights.py
# 62 passed
```

## Root cause

Under the default `rootdir`/`prepend` import mode, `tests/` is placed on `sys.path`
and the repository root is not. The `scripts` package is not installed. Other test
modules import it inside a module-level `pytest.MonkeyPatch.context()` with
`syspath_prepend(ROOT)` (`tests/test_check_docs.py`, `tests/test_severstal.py`).
They also use `monkeypatch.syspath_prepend` per test (`tests/test_local_release.py`).
`tests/test_package_weights.py` imports `from scripts import package_weights`
directly. Confidence is high.

## Remediation

Import `scripts.package_weights` with the repository's established scoped pattern, a
module-level `pytest.MonkeyPatch.context()` with `syspath_prepend(str(ROOT))`. This
does not add a permanent `sys.path` mutation or a `pythonpath` pytest setting. Add a
regression to `tests/test_tooling_boundaries.py` that collects every test module
importing `scripts`, each in its own fresh pytest subprocess, and requires success.

## Architecture

See [architecture.json](architecture.json): `impact: none`, test-only import change.

## Documentation

No documented command or contract changes; record the no-change reason in the fix.
