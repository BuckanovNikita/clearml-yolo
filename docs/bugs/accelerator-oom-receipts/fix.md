# Accelerator OOM receipt fix

Date: 2026-11-06. Assessment: [assessment.md](assessment.md).

The existing CUDA probe worker now recognizes both the legacy typed CUDA
OutOfMemoryError and a typed AcceleratorError carrying integer `error_code=2`.
The native C++ binding supplies this field; the Python-only constructor and Torch
stubs omit it, so the existing SDK owner uses a documented narrow `getattr`.
Messages never determine classification. Missing, malformed or other codes,
arbitrary RuntimeError and mixed execution/cleanup ExceptionGroup remain errors.

The failing receipt regression was captured before the runtime change. CPU tests
cover opaque code-2 diagnostics, misleading OOM wording with invalid codes, the
legacy exception, arbitrary RuntimeError with code 2 and a cleanup failure grouped
with OOM. Existing receipt identity and process-result checks are retained.

## Architecture and scope

The [architecture record](architecture.json) was validated before implementation.
The only runtime change is in the existing worker SDK boundary; there are no new
imports, effects, dependency exceptions or receipt fields. Existing import rules
and architecture negative cases pass. The task-owned diff consists of the worker
classification branch, focused receipt tests and this bug directory. Pre-existing
DINOv3, campaign and force changes are excluded from this fix's ownership.

No dependency pins, upstream code, search grid or frozen candidate were changed.
Confirmed OOM at the aligned minimum 8 may yield `no_capacity`; this correction
does not assert that the model fits or that cleanup succeeded. Parent-owned native
replay, integrated verification and fresh independent review remain acceptance gaps.
See [test.md](test.md) for executed evidence.
