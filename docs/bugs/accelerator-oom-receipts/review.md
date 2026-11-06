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
