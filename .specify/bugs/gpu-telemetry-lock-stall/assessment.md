# Bug Assessment: gpu-telemetry-lock-stall

- **Slug**: `gpu-telemetry-lock-stall`
- **Assessed**: 2026-10-04
- **Source**: user-authorized remediation plan and historical October 3 review
- **Implementation baseline**: `4c0e627`
- **Severity**: high
- **Verdict**: confirmed defect

## Symptom and evidence

Queue admission and contraction held the registry transaction lock during telemetry. Event-blocked telemetry prevented unrelated queue transactions.

Historical source reports remain unchanged locally. This working assessment records the
relevant observation without requiring those unpublished files. The regression tests
exercise the affected public behavior or boundary using isolated fixtures.

## Root cause and accepted remediation

Affected implementation: `gpu_queue.py` under `src/clearml_yolo`.

Probe outside transactions, then reread and validate live registry state before FIFO admission or contraction.

## Reproduction and verification

Run the maintained regression equivalent from the repository root:

```bash
uv run --no-sync pytest tests/test_gpu_queue.py -q
```

The corrected assertion is the expected behavior; it must pass after remediation.
See [implementation](fix.md), [verification](test.md), and the self-contained
[finding ledger](../../../docs/review-fixes-20261004.md) for measured results and limits.
