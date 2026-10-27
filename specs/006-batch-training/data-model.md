# Data model

Training profiles identify backend/preset/architecture, nominal/effective shape,
precision, compilation, optimizer, accumulation, EMA, augmentation and dependency
versions. Workload bounds are positive class and per-image object counts.

GPU records retain visible identity, type and total capacity. Measurement grouping uses
GPU name and total-memory capacity; UUIDs preserve provenance. Exact-allocation lookup
matches ordered capabilities and count. Otherwise every distinct target group needs a
compatible single-GPU source. The global batch is positive and divisible by target
world size; per-GPU batch is stored separately.

A trial records requested batch, status, per-rank peaks, bounded step evidence and
failure diagnostics. CUDA OOM is capacity evidence; timeout, crash, nonfinite, missing
asset and contamination are failures. A saved case is usable only after successful
fresh repetition. A ceiling-limited case is labelled explicitly. A versioned catalogue
retains successful and failed cases with provenance; atomic locked replacement preserves
completed peer cases. Requested null and chosen-batch provenance are separate records.

A typed resolved recommendation identifies its measured/extrapolated origin, target
allocation, source estimate keys, global/per-GPU batches and source boundary/ceiling
status. Exact compatible measurements take precedence, including readable legacy
multi-GPU cases. Extrapolation uses N times the smallest compatible single-GPU capacity;
identical hardware shares a source. Source workload and training-profile checks remain
strict. Extrapolation creates no trial or stored measured case. The persisted settings
and evidence schema remain readable; new searches interpret the CLI ceiling per GPU
because every trial uses a single-GPU profile.
