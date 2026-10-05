# Bug Assessment: empty-settings-break-replay

- **Slug**: `empty-settings-break-replay`
- **Assessed**: 2026-10-04
- **Source**: user-authorized remediation plan and historical October 3 review
- **Implementation baseline**: `4c0e627`
- **Severity**: medium
- **Verdict**: confirmed defect

## Symptom and evidence

Canonical replay normalization dropped explicit empty values, so an intended override could revert to a default.

Historical source reports remain unchanged locally. This working assessment records the
relevant observation without requiring those unpublished files. The regression tests
exercise the affected public behavior or boundary using isolated fixtures.

## Root cause and accepted remediation

Affected implementation: `clearml_session.py` under `src/clearml_yolo`.

Preserve explicit empty executable replay settings and native groups; separately prune irrelevant empty result provenance.

## Reproduction and verification

Run the maintained regression equivalent from the repository root:

```bash
uv run --no-sync pytest tests/test_clearml_session.py -q
```

The corrected assertion is the expected behavior; it must pass after remediation.
See [implementation](fix.md), [verification](test.md), and the self-contained
[finding ledger](../../../docs/review-fixes-20261004.md) for measured results and limits.
