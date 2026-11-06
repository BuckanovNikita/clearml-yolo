# Bug review: unreadable derived DINOv3 checkpoint blocks cache repair

## Fresh independent fix review — 2026-11-07

Scope: fix commit `d084dd2`, landed on `master` as `96581a4`
(`src/clearml_yolo/adapters/deim/hf_weights.py`,
`tests/test_dinov3_hf_weights.py`) with [assessment.md](assessment.md),
[fix.md](fix.md), [test.md](test.md) and [architecture.json](architecture.json).
The reviewer had fresh context and did not write the fix.

Verdict: **approve**. No blocking finding.

Confirmed by the reviewer:

- Only the `torch.load` call in `_reload` is wrapped, and every failure is re-raised as
  `ValueError` chained with `from error`. `_cached` already treats `ValueError` as
  "rebuild", so an unreadable checkpoint with a matching receipt is now reconverted.
- The staging reload in `_publish` is outside any handler, so a freshly converted
  checkpoint that fails to reload still raises.
- The only caller, `resolve_backbone` in `adapters/assets/execution.py`, does not catch
  specific exception types, so the type change does not affect it.
- `KeyboardInterrupt` and `SystemExit` derive from `BaseException` and are not caught.
- A systemic `torch.load` failure is not hidden: the cache check causes one
  reconversion, and the staging reload then raises again.
- Under Torch 2.14.1, `torch.load(weights_only=True)` on the three test payloads raises
  `TypeError`, `KeyError` and `IndexError`; none is in the old tuple, so the regression
  fails without the fix. `repaired == result` proves that a rebuild happened.
- `tests/test_dinov3_hf_weights.py` passed (45 tests) in the reviewer's run.

Findings and dispositions:

| Severity | Finding | Disposition |
| --- | --- | --- |
| low | `except Exception` also relabels `MemoryError`. In the staging reload, a real out-of-memory error surfaces as "Unreadable converted DINOv3 checkpoint" (`ValueError`) with `MemoryError` as the chained cause. | Kept as is; the reviewer's documented alternative is recorded in [fix.md](fix.md#known-behaviour). The cause is chained, so the information is preserved. |
| low | No test covers the staging-reload failure path or the exception chaining. | Not added in this release; recorded as a follow-up in [fix.md](fix.md#follow-ups). |
| info | Architecture acceptance was blocked only by `review.status: pending`. | Resolved: [architecture.json](architecture.json) records this review as accepted. |

Limits: CPU only. The reviewer did not rerun the full suite; it relied on
[test.md](test.md).
