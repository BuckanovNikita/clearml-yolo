# Bug Assessment: clearml-failure-self-abort

- **Slug**: `clearml-failure-self-abort`
- **Assessed**: 2026-10-04
- **Source**: user-authorized remediation plan and historical October 3 review
- **Implementation baseline**: `4c0e627`
- **Severity**: high
- **Verdict**: confirmed defect

## Symptom and evidence

Failed status was published while the SDK watchdog was active, causing self-abort and replacing the intended failure with stopped status. The historical live upload-rejection run exited 137 before its exception catcher.

Historical source reports remain unchanged locally. This working assessment records the
relevant observation without requiring those unpublished files. The regression tests
exercise the affected public behavior or boundary using isolated fixtures.

## Root cause and accepted remediation

Affected implementation: `clearml_session.py` under `src/clearml_yolo`.

Close the SDK task before obtaining a fresh handle and marking failed; preserve the original computation error during SDK or local cleanup failures.

## Reproduction and verification

Run the maintained regression equivalent from the repository root:

```bash
uv run --no-sync pytest tests/test_clearml_session.py -q
```

The corrected assertion is the expected behavior; it must pass after remediation.
See [implementation](fix.md), [verification](test.md), and the self-contained
[finding ledger](../../../docs/review-fixes-20261004.md) for measured results and limits.
