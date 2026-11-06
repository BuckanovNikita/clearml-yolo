# Bug verification: unreadable derived DINOv3 checkpoint blocks cache repair

- Slug: `dinov3-cache-reload-errors`.
- Tested: 2026-11-07, branch `review/wp2a-20261107`.
- Assessment: [assessment.md](assessment.md). Fix: [fix.md](fix.md).
- Result: verified on CPU; release pending.

## Checks performed

| Check | Command | Result | Notes |
| --- | --- | --- | --- |
| Original path, before fix | `pytest -q -p no:cacheprovider tests/test_dinov3_hf_weights.py -k unreadable` | fail (expected) | 6 failed: TypeError, KeyError, IndexError for presets l and x |
| Original path, after fix | same file, all tests | pass | 45 passed |
| Related suites | plus `tests/test_model_assets_loading.py tests/test_deim_backend.py` | pass | 111 passed |
| Full offline suite | `env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES='' nice -n19 uv run --frozen --no-sync pytest -q -p no:cacheprovider` | pass | 4817 passed, 30 skipped, 81 deselected, exit 0 (18 min) |
| Lint and types | `ruff check .`; `mypy` on the two changed files | pass | the commit hooks rerun ruff, mypy, vulture and lint-imports on the whole tree |
| Documentation | `python scripts/check_docs.py --all` | pass | rerun 2026-11-07 at `4e9c832`, after this record existed: 273 Markdown files, 0 issues (the earlier 268 predated the record) |

All pytest commands ran with `CUDA_VISIBLE_DEVICES=''` under
`nice -n19 uv run --frozen --no-sync`.

Deviation from the requested `pytest -n4`: this environment has no pytest-xdist, so
the suite ran serially. Plain `uv run` cannot re-lock here because `digital-metrics`
is missing from the registry, so `--frozen --no-sync` was used.

## Residual risks

- No GPU, live stand or native conversion run; the change only affects error
  normalization before the existing reconversion path.
- The architecture record review is pending; fresh independent review, the patch
  release and the paired queue check remain open (remaining-work plan T2a.2).

## Documentation stage

Reviewed `docs/model-assets.md` lines 186-187, which already promise that corrupt
derived files are rebuilt. No contract or portable usage-skill change is needed.
