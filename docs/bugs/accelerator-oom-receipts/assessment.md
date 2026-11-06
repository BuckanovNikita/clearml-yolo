# Accelerator OOM receipt assessment

- Date: 2026-11-06.
- Slug: `accelerator-oom-receipts`.
- Source: final-candidate DEIM X batch-8 native rank failure.
- Verdict: confirmed typed error-classification defect; no capacity result accepted.

## Observation and cause

The retained native traceback raises `torch.AcceleratorError` from DEIM criterion
indexing, with a CUDA out-of-memory driver diagnostic. The worker recognizes only
`torch.cuda.OutOfMemoryError`, so it writes `status=error` and the search fails.
These are separate RuntimeError subclasses in installed Torch 2.14.1+cu130.

The exact installed Torch revision is
`5c4886908584029761b579af026dcfb627c84070`. Its
[exception binding](https://github.com/pytorch/pytorch/blob/5c4886908584029761b579af026dcfb627c84070/torch/csrc/Exceptions.cpp#L277)
constructs the Python exception and sets integer `error_code` from the native
error. Installed CUDA headers independently define runtime
`cudaErrorMemoryAllocation` and driver `CUDA_ERROR_OUT_OF_MEMORY` as code 2.
The inspected installed header locations were `nvidia/cu13/include/cuda.h:2529`
and `nvidia/cu13/include/driver_types.h:211`. Python-only AcceleratorError constructors omit this field; CPU reflection
confirmed that assigning native-shaped `error_code=2` still misses the current
OutOfMemoryError branch, without initializing CUDA. No GPU allocation test was run
for this assessment.

## Remediation and architecture

Use the existing CUDA-only worker boundary to recognize the existing typed
OutOfMemoryError or a typed AcceleratorError with an integer native error code 2.
Missing, malformed and other codes remain errors. Never infer capacity from
arbitrary diagnostic text, and never unwrap an execution/cleanup ExceptionGroup
to discard its failure. Preserve status schema, identity and atomic publication.

The [architecture record](architecture.json) retains Torch SDK ownership in the
existing worker adapter; it introduces no import exceptions or new effects.
The test file owns CPU-only receipt regressions. No dependency, upstream source,
scientific training setting or eight-aligned search policy changes. An OOM at the
minimum aligned batch 8 may establish genuine `no_capacity` after required cleanup;
it does not prove a successful smaller candidate or fresh winner confirmation.
The independent L execution/cleanup failure remains unresolved.

## Task ledger

- [x] Inspect native failure, installed definitions and exact upstream binding.
- [x] Validate architecture plan before code edits (validator exit 0).
- [x] Capture CPU regression failure, apply minimal classification correction.
- [x] Verify bounded receipt, static, import and documentation checks.
- [ ] Parent rebuilds frozen source/profile identity and verifies native OOM evidence.
- [ ] Parent completes integrated canonical, final review and release gates.

Public CLI/configuration, finite guards, search policy and receipt fields do not
change. Existing guidance requiring confirmed native OOM and preserving cleanup
failures remains applicable; this dated report documents the added SDK exception
representation. Final documentation reconciliation remains parent-owned.
