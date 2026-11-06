# Scoped campaign improvements review

## WP2a integrated source review — 2026-11-07

Scope: `git diff v0.45.1 v0.46.0 -- src tests`, the scoped campaign export changes:
bulk `_enrich_rows` conversion (`core/evaluation/result_rows.py`), the Torchvision
nonfinite-loss message and the scalar capture message. Lens: OOM receipts and scoped
campaign export, followed by a skeptic pass.

Checked: a temporary differential Hypothesis test compared the v0.45.1 `iterrows`
implementation with the new bulk conversion. It compared the export CSV
(`float_format` `%.17g`) and column dtypes over GT and prediction rows, missing,
NaN, infinite, integer, float and text boxes, null labels, mixed metadata, nullable
`Int64`, string, datetime, timedelta, category, boolean-extension and float32 columns.
700 examples found no counterexample. The Torchvision message is built before
`backward()` from a scalar int64 `image_id`, so it cannot mask the
`FloatingPointError`; the capture message still raises before any journal write.
Focused suites passed. The temporary test was not kept.

Findings: none. Verdict: no change required within the stated scope.

Limits: CPU only. The review brief named the constitution and
`docs/project-contracts.md`; the lens report does not confirm reading them.
Architecture acceptance (T2a.4) is separate.
