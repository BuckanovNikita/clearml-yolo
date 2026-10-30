# Interfaces

`cy-batch-estimate --imgsz 960 --classes 150 --objects-per-image 300` selects the default
catalogue and outputs GPU counts 1 through visible count. `--devices` chooses ordered
hardware; `--gpu-counts` filters recommendations for the first N selected devices and
launches no additional searches. Measure once per model/resolution/profile and distinct
GPU name/capacity, on the first idle unassigned selected representative when evidence
is needed. Independent cases run in separate processes, each pinned to its GPU for
the full search. Optional positive `--jobs N` limits concurrent cases; the default
uses available selected GPUs and `--jobs 1` runs serially. Compatible cache hits need
no idle device. Candidate/optimizer trials within one case remain sequential.
Every trial and winner confirmation uses exactly one GPU. `--search-limit` is the
per-GPU ceiling (default 1024); extrapolated global batches may exceed it. Refresh,
memory-budget and trial-timeout controls apply to actual single-GPU measurements.
The trial timeout is not a timeout for the complete search.

New `SearchSettings.search_strategy` values default to `memory_guided_v1`; explicit
`exponential_binary_v1` retains the historical transition policy. Guided search starts
at 1 and 2, predicts from full successful memory observations with bounded growth,
falls back to doubling without a positive slope and uses exact binary refinement
after an observed capacity bound. Full warm-up/measured steps, all optimizer paths,
validation and fresh confirmation remain required. Numerical recovery preserves
the cause and the independently confirmed last good candidate, which can differ
between strategies.

Catalogues read schemas 1/2/3 and write schema 3 with explicit per-case strategies.
Missing historical strategies use legacy replay and preserve source keys. Invalid
schema/strategy combinations and forged trial histories fail without rewriting files.
Refresh saves pending evidence before case launch. Only the invocation owner promotes
confirmed evidence after matching the token/key receipt, successful exit and cleanup.
Ordinary measurement or case-result failures leave peers running. Unrecoverable
process-supervision failures stop the invocation while preserving accepted results.
Cancellation cleans only owned process
trees. Slots with unverifiable cleanup cannot host another case in that invocation.

`cy-train ... ultralytics.batch=null` and native `model.train.batch=null` request strict
local lookup. Queue snapshots preserve null. Compatibility and actual dataset bounds
must pass before native execution. Prefer compatible exact-allocation evidence;
otherwise require compatible single-GPU sources for every target hardware group and
derive `N × min(per_gpu_capacities)`. Typed recommendations retain measured/extrapolated
origin, target allocation, source keys and boundary/ceiling status. Stored trials remain
unchanged. Unsupported/custom profiles require explicit batch. An OOM during training
keeps normal failure behavior without automatic retry or hidden batch reduction.

Worker requests carry backend configuration, prepared dataset, output, optional
augmentation and world-size/rank settings. Workers never create ClearML tasks. Typed
results carry native evidence and scalar events for owner publication. Rank failure
terminates its cooperating owned rank group before any subsequent trial or queue
contraction; this does not apply fail-fast semantics to independent estimator cases.

Fresh configuration trees include ordinary YAML command bases and transitive defaults;
explicit distinct schema references retain validation without automatic matching.
