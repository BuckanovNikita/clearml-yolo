# Bug Verification: split-output-traversal

- **Slug**: `split-output-traversal`
- **Tested**: 2026-10-04
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Summary

The maintained regression equivalent passes after remediation. The accepted behavior and
original symptom are recorded in the assessment; broader pinned and candidate-dependency
checks found no remaining regression.

## Checks Performed

| Check | Command / Action | Result | Notes |
|---|---|---|---|
| Corrected reproduction | `uv run --no-sync pytest tests/test_metrics.py tests/tests/test_report.py tests/tests/test_review_regressions.py -q` | pass | Included in the parent full suite. |
| Regression suite | `uv run --no-sync pytest -q` | pass | Both pinned and candidate dependency environments. |
| Static contracts | `uv run --no-sync ruff check .`, `uv run --no-sync mypy .`, `uv run --no-sync lint-imports` | pass | No lint/type/import violations. |
| Documentation | Markdown parsing, local links and `git diff --check` | pass | Working records and affected contracts. |

## Output Excerpts

The parent full suites each reported `917 passed, 9 skipped`; the later dashboard-freshness
correction passed all 136 affected metrics, comparison-assembly and session tests.
Detailed dated acceptance and live checks are in [verification evidence](../../../docs/verification-20261004.md).

## Residual Risks

Actual metrics/report producers exercised with traversal-shaped split; no full native arbitrary-split pipeline required.

See the acceptance report for the explicit platform and optional integration exclusions.
Tests using fake SDK/telemetry boundaries do not establish physical driver or multi-GPU behavior.

## Recommendation

Close this finding with the accepted contract and recorded limits. Keep the fix PR unmerged
for the user's review.
