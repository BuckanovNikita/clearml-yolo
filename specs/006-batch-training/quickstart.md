# Validation guide

Run from a prepared source environment; use isolated CY_HOME/output roots and explicit
ClearML project/tags for native execution. No test may stop unrelated GPU workloads.

```bash
CUDA_VISIBLE_DEVICES='' uv run --frozen --no-sync python scripts/verify.py
CUDA_VISIBLE_DEVICES='' uv run --frozen --no-sync python scripts/verify.py --docs
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn --devices 0 --jobs 1
cy-init-config config-example --command cy --model fcos/resnet50_fpn
cy --config-path config-example --config-name cy --cfg job
```

Verify real single-GPU searches, saved success/failure records, rerun/resume and
refresh. Each measured hardware group uses its first idle selected representative;
other workloads remain untouched. Check that every trial has one GPU regardless of
`--gpu-counts`, that identical hardware shares evidence, and that mixed-hardware output
requires a compatible source for every name/capacity group. Verify measured/extrapolated
provenance, ceiling propagation, totals above the per-GPU search ceiling, divisibility,
missing/stale/failed sources, dataset bounds and worker-assigned queue allocations.
The estimator gate no longer requires an exhaustive distributed probe matrix.

Verify that new cases record `memory_guided_v1` and a schema-3 catalogue. Load frozen
schema-1/2 records without rewriting their bytes; their original keys and legacy trial
sequence must still validate. Reject unknown strategies and mismatched histories.
Check exact confirmed capacity and fewer trials on deterministic linear-memory cases,
plus nonlinear/flat memory growth, observed OOM/budget refinement, ceilings and
numerical recovery. A numerical limit may retain a different last good batch after
candidate ordering changes; it must never claim a measured maximum.

For independent-case execution, compare automatic concurrency with `--jobs 1` on the
same selected hardware and models. On a host with two idle compatible GPUs:

```bash
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn \
  --devices 0,1 --jobs 2 --refresh
```

Verify simultaneous cases use different pinned UUIDs, one case retains its GPU for
the complete search, and identical hardware is not measured twice for the same model.
Real CPU subprocess tests separately exercise overlap, peer survival after failure,
SIGINT/SIGTERM, detached descendants and cleanup before slot reuse. Confirm that a
completed worker receipt alone cannot publish success: shared progress stays unusable
until the parent validates identity, process exit and cleanup. Refresh interrupted
before worker startup must not expose the prior success. Concurrent catalogue writers
must preserve peer cases. These process checks do not establish physical GPU speedup.

Record native legacy/guided comparison trial counts, elapsed times and outcomes using
matching prepared assets, workload and idle hardware. Preserve actual limitations in
dated evidence; ordinary test success is not a native benchmark result.

Separately test all six FCOS checkpoint round trips. Real multi-GPU training checks
require at least two idle visible GPUs and must cover each backend plus peer
failure/cleanup; a CPU or single-GPU estimator pass cannot replace that evidence.

The physical harness runs the public pipeline for DEIMv2, RF-DETR, Faster R-CNN
and FCOS through production supervised workers. First run its four success cases,
then all sixteen cases, including rank crash, actual CUDA OOM and owner cancellation
followed by recovery. Run serially on an idle host with two selected GPUs:

```bash
uv run --frozen --no-sync pytest tests/test_native_ddp_gpu.py \
  -k native_backend_pipeline --run-ddp-gpu --ddp-devices=0,1 \
  --ddp-clearml-project=clearml-yolo-native-ddp \
  --ddp-artifacts=.tmp/native-ddp-results -ra -vv
uv run --frozen --no-sync pytest tests/test_native_ddp_gpu.py \
  -k native_backend --run-ddp-gpu --ddp-devices=0,1 \
  --ddp-clearml-project=clearml-yolo-native-ddp \
  --ddp-artifacts=.tmp/native-ddp-results -ra -vv
```

These representative cases use random initialization, FP32, resolution 128 and one
epoch. They verify real NCCL execution, sharding, accumulation, model/optimizer/EMA
agreement, unique uneven validation, checkpoint ownership, one ClearML owner and
downloaded checkpoint reload. They do not replace default-precision/pretrained
acceptance or the separate single-GPU estimator/extrapolation checks. Raw requests, process identities, receipts,
logs and publication evidence are retained under the explicit artifact directory.
