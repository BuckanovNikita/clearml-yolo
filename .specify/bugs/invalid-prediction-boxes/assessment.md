# Bug Assessment: Invalid prediction boxes stop evaluation

- **Slug**: invalid-prediction-boxes (generated from the supplied plan)
- **Created**: 2026-10-05
- **Source**: user-supplied implementation plan
- **Verdict**: valid
- **Severity**: medium

## Report

Warn and drop prediction boxes with zero area, reversed corners, missing,
nonnumeric or non-finite coordinates before preprocessing and mAP. Apply to
validation, metrics and comparison; preserve raw CSVs. All-invalid predictions
must score as empty and unmatched ground truth as false negatives. Preserve valid
scoring, ground-truth validation, unrelated errors and digital-metrics unchanged.

## Reproduction

Call `tasks.metrics._prepare` with a cat prediction `(0, 0, 0, 10)`, confidence
0.8, and valid validation ground truth `(0, 0, 10, 10)`. On 2026-10-05 the real
installed dependency raises `ValueError: Predictions boxes must have ordered
corners and positive area.`

## Root Cause and Code Paths

High confidence: `comparison.scoring.prepare_predictions` calls the strict
upstream preprocessor. `evaluate_split` independently sends raw predictions to
mAP. `tasks.metrics._prepare` and `tasks.compare._scored` construct both inputs;
`tasks.val.validate` delegates to metrics. Sanitizing just the prepared frame
would leave mAP failing.

## Proposed Remediation

Add a shared geometry filter in `comparison/scoring.py`. Apply it to in-memory
raw evaluation copies in `tasks/metrics.py` and `tasks/compare.py`, before those
copies split into preprocessing and mAP paths. Retain valid rows and their order;
keep existing prepared-frame indexing so payload and matches use the same frame.
Warn with dropped/total counts, per-reason row counts and at most five image names.
Missing required columns remain schema errors; missing coordinate cells are dropped.

Tests: mixed invalid kinds, all-invalid/empty, preprocessing enabled, valid scoring
and mAP parity, both 640 and 960 inference settings, payload/match identity, raw
CSV preservation, ground-truth and unrelated confidence validation unchanged.

## Documentation Update

Update evaluation safety in `specs/001-release-030/contracts/cli.md` and its summary
in `docs/current-contracts.md`; validate Markdown and local links. Record fix and
verification here. No CLI or configuration examples change.

## Risks and Open Questions

Numeric strings must remain acceptable to upstream scoring. Filtering must not
mutate input artifacts or remove low-confidence valid rows from the raw mAP input.
No unresolved scope questions. No dependency modifications are authorized.
