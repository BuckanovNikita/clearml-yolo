# Bug verification: unreadable derived DINOv3 checkpoint blocks cache repair

- Slug: `dinov3-cache-reload-errors`.
- Tested: 2026-11-07, branch `review/wp2a-20261107`.
- Assessment: [assessment.md](assessment.md). Fix: [fix.md](fix.md).
- Result: verified on CPU; released in CY 0.46.1 (status updated 2026-11-07, see
  [Release and paired check](#release-and-paired-check--2026-11-07)).

## Checks performed

| Check | Command | Result | Notes |
| --- | --- | --- | --- |
| Original path, before fix | `pytest -q -p no:cacheprovider tests/test_dinov3_hf_weights.py -k unreadable` | fail (expected) | 6 failed: TypeError, KeyError, IndexError for presets l and x |
| Original path, after fix | same file, all tests | pass | 45 passed |
| Related suites | plus `tests/test_model_assets_loading.py tests/test_deim_backend.py` | pass | 111 passed |
| Full offline suite | `env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest --testmon-noselect -q -p no:randomly` | pass | 4817 passed, 30 skipped, 81 deselected, exit 0 (18 min); command corrected 2026-11-07 to the one actually run |
| Lint and types | `ruff check .`; `mypy` on the two changed files | pass | the commit hooks rerun ruff, mypy, vulture and lint-imports on the whole tree |
| Documentation | `python scripts/check_docs.py --all` | pass | rerun 2026-11-07 at `e1973ff` (pre-rebase `4e9c832`), after this record existed: 273 Markdown files, 0 issues (the earlier 268 predated the record) |

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
  Closed 2026-11-07: the review is in [review.md](review.md) and the release and
  paired check are recorded below.

## Documentation stage

Reviewed `docs/model-assets.md` lines 186-187, which already promise that corrupt
derived files are rebuilt. No contract or portable usage-skill change is needed.

## Release and paired check — 2026-11-07

The fix landed on `master` as `96581a4` (rebased from `d084dd2`) and was released as
CY 0.46.1: release commit `1ff9a66fd4bd1b4b94fae396a433ab89e5ad6990`, annotated tag
`v0.46.1`, created by the post-commit release hook.

Before landing, on the rebased branch tip `4428ec7` (same `src` and `tests` as the
release): `ruff check .`, strict `mypy .` (465 files), `vulture` and `lint-imports`
(52 contracts kept) passed, and
`env -u PYTEST_ADDOPTS CUDA_VISIBLE_DEVICES= nice -n19 uv run --frozen --no-sync pytest --testmon-noselect`
gave 4817 passed, 30 skipped, 81 deselected, exit 0 (19 min 45 s). The commit hooks
also passed on the commit that triggered the release.

Paired CY/queue check, run from the cy-queue checkout with the CY `.venv` (no queue
worker was running):

| Item | Value |
| --- | --- |
| CY source | `1ff9a66fd4bd1b4b94fae396a433ab89e5ad6990`, version 0.46.1 |
| cy-queue source | `0c486b5257da8950932aded99dc2a2f1b3680286` (`origin/main`), version 0.1.9, requirement `clearml-yolo>=0.38,<0.47` |
| `uv pip install -e ../clearml-yolo -e .` | normal resolution, installed `clearml-yolo==0.46.1`, `cy-queue==0.1.9` |
| `uv pip check` | all 281 installed packages compatible |
| Installed metadata | `clearml-yolo` 0.46.1, `cy-queue` 0.1.9 |
| Queue `pytest -q` | 584 passed, 7 deselected (physical `ddp_gpu` opt-ins, waived) |
| `cy-queue --help` | exit 0 |
| Queue `ruff check .`, `ruff format --check .` | passed; 222 files already formatted |
| Queue `mypy .`, `lint-imports` | no issues in 70 files; 2 contracts kept |

Limits: CPU only, `CUDA_VISIBLE_DEVICES` empty; no GPU, native conversion or live
stand run.
