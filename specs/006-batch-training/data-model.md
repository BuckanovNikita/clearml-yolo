# Data model

Training profiles identify backend/preset/architecture, nominal/effective shape,
precision, compilation, optimizer, accumulation, EMA, augmentation and dependency
versions. Workload bounds are positive class and per-image object counts.

GPU records retain visible identity, type and total capacity. Measurement grouping uses
GPU name and total-memory capacity; UUIDs preserve provenance. Exact-allocation lookup
matches ordered capabilities and count. Otherwise every distinct target group needs a
compatible single-GPU source. The global batch is positive and divisible by target
world size; per-GPU batch is stored separately.

A search settings record identifies `memory_guided_v1` or `exponential_binary_v1`.
New API/CLI settings default to memory-guided search. Discovery starts at batches 1
and 2. For the two latest successful under-budget aggregate peaks `(b1, m1)` and
`(b2, m2)`, positive growth predicts
`b2 + ((budget - m2) * (b2 - b1)) // (m2 - m1)`. Clamp the next candidate to
`lower + 1` through `min(4 * lower, ceiling)`. Missing/nonpositive slopes use
doubling. Only observed capacity failures establish bounds for binary refinement.
The strategy changes candidate selection, never the required trial evidence.

A trial records requested batch, status, per-rank peaks, bounded step evidence and
failure diagnostics. CUDA OOM is capacity evidence; timeout, crash, nonfinite, missing
asset and contamination are failures. A saved case is usable only after successful
fresh repetition. After discovery-time nonfinite computation, one fresh successful
repeat of the last under-budget successful candidate yields `numerically_limited`.
It preserves the numerical failure and makes no capacity-maximum claim. Candidate
ordering can change the last good batch retained after a numerical failure. Any failed
confirmation remains unusable. Ceiling-limited cases are also labelled explicitly.
A versioned catalogue retains successful and failed cases with provenance; atomic
locked replacement preserves completed peer cases. Schemas 1 and 2 remain readable
without rewriting; missing historical strategies imply `exponential_binary_v1`.
Legacy keys retain their original canonical payload without the added strategy field.
Ordinary saves write schema 3 with explicit strategies for historical and new cases.
Schemas 1/2 cannot contain guided histories, and schema 1 still excludes the
`numerically_limited` status. Unknown strategies or histories inconsistent with their
recorded strategy fail validation.
Requested null and chosen-batch provenance are separate records.

Case requests carry a unique case token, expected estimate key, single-GPU profile,
workload/settings, catalogue path and isolated output path. Completion receipts pair
the same token/key with a fully validated case. The parent pins the profile's UUID
and persists failed/pending evidence before launch. The child persists progress but
keeps any independently confirmed result unusable until the parent verifies receipt
identity, successful process exit and owned descendant cleanup. Cases are deduplicated
by estimate key before dispatch; positive optional `--jobs` caps independent case
concurrency, without changing case identity or measurement compatibility.

A typed resolved recommendation identifies its measured/extrapolated origin, target
allocation, source estimate keys, global/per-GPU batches, source boundary/ceiling/numerical
status and diagnostics. Numerical limitation takes precedence over ceiling and validated
status. Exact compatible measurements take precedence, including readable legacy
multi-GPU cases. Extrapolation uses N times the smallest compatible single-GPU capacity;
identical hardware shares a source. Source workload and training-profile checks remain
strict. Extrapolation creates no trial or stored measured case. The persisted settings
and evidence schema remain readable; new searches interpret the CLI ceiling per GPU
because every trial uses a single-GPU profile.
