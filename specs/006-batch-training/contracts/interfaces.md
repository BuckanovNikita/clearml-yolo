# Interfaces

`cy-batch-estimate --imgsz 960 --classes 150 --objects-per-image 300` selects the default
catalogue and outputs GPU counts 1 through visible count. `--devices` chooses ordered
hardware; `--gpu-counts` filters recommendations for the first N selected devices and
launches no additional searches. Measure once per model/resolution/profile and distinct
GPU name/capacity, on the first idle selected representative when evidence is needed.
Every trial and winner confirmation uses exactly one GPU. `--search-limit` is the
per-GPU ceiling (default 1024); extrapolated global batches may exceed it. Refresh,
memory-budget and trial-timeout controls apply to actual single-GPU measurements.

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
terminates owned peers before any subsequent trial or queue contraction.

Fresh configuration trees include ordinary YAML command bases and transitive defaults;
explicit distinct schema references retain validation without automatic matching.
