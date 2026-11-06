# Bug fix: unreadable derived DINOv3 checkpoint blocks cache repair

- Slug: `dinov3-cache-reload-errors`.
- Fixed: 2026-11-07, on branch `review/wp2a-20261107` (not released).
- Assessment: [assessment.md](assessment.md).
- Status: applied.

## Changes

| File | Change | Notes |
| --- | --- | --- |
| `src/clearml_yolo/adapters/deim/hf_weights.py` | modified | `_reload` normalizes any `torch.load` failure to `ValueError` with the cause chained |
| `tests/test_dinov3_hf_weights.py` | added test | `test_unreadable_derived_checkpoint_with_matching_receipt_is_rebuilt` |

`_cached` keeps its exception tuple; the normalized `ValueError` reaches it. The
staging reload in `_publish` still raises. Ruff accepts the broad catch because it
re-raises; a comment records why the error set is open-ended.

## Tests added

`test_unreadable_derived_checkpoint_with_matching_receipt_is_rebuilt[l|x-type-error|key-error|index-error]`
writes each payload with a matching receipt and requires `_publish` to return the
original record.

## Local verification

- Before the fix: `CUDA_VISIBLE_DEVICES='' nice -n19 uv run --frozen --no-sync pytest -q
  -p no:cacheprovider tests/test_dinov3_hf_weights.py -k unreadable` gave 6 failed
  (TypeError, KeyError, IndexError for each preset).
- After the fix: the same file gave 45 passed; with `tests/test_model_assets_loading.py`
  and `tests/test_deim_backend.py`, 111 passed. `ruff check .` passed.
- Full suite and hooks: see [test.md](test.md).

## Deviations from assessment

None.

## Known behaviour

Recorded 2026-11-07 after the [fix review](review.md). The broad catch also turns
`MemoryError` into `ValueError`. During the cache check this causes one reconversion,
which the assessment accepts. During the staging reload in `_publish`, a real
out-of-memory error surfaces as `ValueError("Unreadable converted DINOv3 checkpoint:
...")` naming an already deleted temporary path, with `MemoryError` as the chained
`__cause__`. Read the cause when diagnosing such a failure.

## Follow-ups

- Patch release and the paired queue check (remaining-work plan T2a.2) are outside
  this branch step.
- Review note, not fixed here: a hard kill during conversion leaves `.conversion-*`
  staging directories behind.
- Review follow-up, not done here: a test for the staging-reload failure path that
  asserts the `ValueError` from `_publish`, a chained `TypeError` cause and no
  published `.pth`/`.json` file.
