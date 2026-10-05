# Bug Assessment: comparison-invalid-q

- **Slug**: `comparison-invalid-q`
- **Assessed**: 2026-10-04
- **Source**: user-authorized remediation plan and historical October 3 review
- **Implementation baseline**: `4c0e627`
- **Severity**: medium
- **Verdict**: confirmed defect

## Symptom and evidence

Invalid false-discovery probabilities produced misleading significance verdicts. Historical statistical probes reproduced values outside the valid domain.

Historical source reports remain unchanged locally. This working assessment records the
relevant observation without requiring those unpublished files. The regression tests
exercise the affected public behavior or boundary using isolated fixtures.

## Root cause and accepted remediation

Affected implementation: `comparison/significance.py, comparison/assemble.py, tasks/compare.py` under `src/clearml_yolo`.

Validate finite q in [0,1] before statistical computation or verdict decisions.

## Reproduction and verification

Run the maintained regression equivalent from the repository root:

```bash
uv run --no-sync pytest tests/test_review_regressions.py -q
```

The corrected assertion is the expected behavior; it must pass after remediation.
See [implementation](fix.md), [verification](test.md), and the self-contained
[finding ledger](../../../docs/review-fixes-20261004.md) for measured results and limits.
