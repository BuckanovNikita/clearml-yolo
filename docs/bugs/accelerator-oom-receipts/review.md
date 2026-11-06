# Accelerator OOM receipt review

## WP2a integrated source review — 2026-11-07

Scope: `git diff v0.45.1 v0.46.0 -- src tests`, OOM receipt classification in
`adapters/integrations/probe_worker.py`, failure preference in `batch_probe.py` and
the estimator scheduler. Lens: OOM receipts and scoped campaign export, followed by a
skeptic pass.

Checked: on installed Torch 2.14.1+cu130, `torch.cuda.OutOfMemoryError` is not a
subclass of `torch.AcceleratorError` (printed MRO). Classification requires an
integer `error_code` equal to 2: `True`, floats and missing codes stay `error`.
Message text is never used and exception groups are not unwrapped, matching the
[assessment](assessment.md). Receipts are still published atomically, the worker
exits 1 on OOM, `batch_probe.py` still prefers the `oom` receipt, and the scheduler
still quarantines a GPU after incomplete cleanup. Focused suites passed.

Findings: none. Verdict: no change required within the stated scope.

Limits: CPU only; a real CUDA OOM, native replay and multi-GPU behaviour were not
exercised. The review brief named the constitution and `docs/project-contracts.md`;
the lens report does not confirm reading them.

### Scope correction and rules lens — 2026-11-07

A follow-up agent with fresh context, part of the same WP2a workflow rather than an
independent reviewer, read `.specify/memory/constitution.md` (300 lines) and
`docs/project-contracts.md` (331 lines) in full and checked the topic above against them.

Principle I: classification reads `error_code` with `getattr` on the opaque Torch
exception, a third-party boundary the principle allows, and never uses message text.
Principle IV: evidence stays CPU-only and claims no real OOM. No new finding.

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
