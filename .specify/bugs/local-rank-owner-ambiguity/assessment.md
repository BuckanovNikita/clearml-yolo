# Bug Assessment: local-rank-owner-ambiguity

- **Slug**: `local-rank-owner-ambiguity`
- **Assessed**: 2026-10-04
- **Source**: user-authorized remediation plan and historical October 3 review
- **Implementation baseline**: `4c0e627`
- **Severity**: medium
- **Verdict**: supported-launch ambiguity resolved by user decision

## Symptom and evidence

An inherited LOCAL_RANK suppressed top-level tracking ownership. The earlier support ambiguity is resolved: ownerless rank launches are unsupported.

Historical source reports remain unchanged locally. This working assessment records the
relevant observation without requiring those unpublished files. The regression tests
exercise the affected public behavior or boundary using isolated fixtures.

## Root cause and accepted remediation

Affected implementation: `apps/common.py, native_runtime.py, clearml_session.py` under `src/clearml_yolo`.

Reject ownerless rank launches before scheduling; recognize internal descendants using both project owner PID and task identity.

## Reproduction and verification

Run the maintained regression equivalent from the repository root:

```bash
uv run --no-sync pytest tests/test_native_runtime.py tests/tests/test_clearml_session.py tests/tests/test_review_regressions.py -q
```

The corrected assertion is the expected behavior; it must pass after remediation.
See [implementation](fix.md), [verification](test.md), and the self-contained
[finding ledger](../../../docs/review-fixes-20261004.md) for measured results and limits.
