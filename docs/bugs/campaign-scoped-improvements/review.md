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

### Scope correction and rules lens — 2026-11-07

A follow-up agent with fresh context, part of the same WP2a workflow rather than an
independent reviewer, read `.specify/memory/constitution.md` (300 lines) and
`docs/project-contracts.md` (331 lines) in full and checked the topic above against them.

Principle II: `core/evaluation/result_rows.py` imports only pandas, NumPy, the
standard library and core modules, with no effects. Principle IV: evidence stays CPU-only. No new finding.

Scope narrowed: the diff examined is `git diff v0.45.1 v0.46.0 -- src tests`, but the
review covers only the T2a.1 topic named above. Tooling-only test changes in that diff
were outside every lens: `tests/test_verify.py` (removed), `tests/test_local_release.py`
and `tests/test_tooling_boundaries.py` come from `8a1d5a9` (verify.py replaced by prek
hooks) and were not reviewed. `tests/fixtures/docs-compatibility.json`,
`tests/test_docs_compatibility.py` and `tests/test_native_backend_ddp_harness.py` come
from `c16dbb1`; their diffs (the `--force` help text and `False` default, and a stub that
keeps the AdamW default-accelerator probe off CUDA in the CPU harness) were read and are
consistent with forced admission and the harness intent; nothing more was examined.

### Independent rules lens — 2026-11-07

A separate fresh-context reviewer checked the whole runtime diff against the
constitution and `docs/project-contracts.md` and approved it with no rule violation;
see the [DINOv3 review record](../dinov3-hf-native/review.md#independent-rules-lens--2026-11-07).
