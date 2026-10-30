# Training batch estimation

Batch estimation is available from version 0.41.0. See the
[release evidence](../specs/006-batch-training/evidence/release.md) for native verification limits.
Single-GPU estimator acceptance and the separate real multi-GPU training checks
are recorded in the [feature ledger](../specs/006-batch-training/tasks.md).
Configuration examples and CPU tests do not establish native GPU outcomes.

`cy-batch-estimate` measures training capacity locally without creating a ClearML
task. It tests registered pretrained YOLO variants and all registered DEIMv2,
RF-DETR, Faster R-CNN and FCOS presets. It searches once per model, resolution,
training profile and distinct GPU name/total-memory capacity. Identical GPUs share
one measurement. For a hardware group needing measurement, it uses the first idle
GPU in the selected order. Only the probed GPU must be idle; unrelated workloads
remain running. Missing or unidentifiable telemetry fails the measurement.

## Measure selected cases

```bash
cy-batch-estimate --imgsz 960
cy-batch-estimate --imgsz 960 --classes 150 --objects-per-image 300
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn --devices 0,1
```

The default catalogue includes the 44 standard pretrained YOLO detection variants
and all native presets in the [model guide](multi-model-backends.md). YOLO filters
accept a catalogue selector such as `ultralytics/yolo11n` or an asset name such as
`yolo11n.pt`. Custom checkpoints and architectures require an explicit training batch
when no compatible measurement exists.

| Option | Meaning and default |
| --- | --- |
| `--imgsz N` | Required nominal square training resolution |
| `--classes N` | Synthetic foreground classes; 150 |
| `--objects-per-image N` | Synthetic target density for every image; 300 |
| `--models LIST` | Comma-separated catalogue selections; all registered cases |
| `--devices LIST` | Ordered logical indexes within inherited CUDA visibility; all visible GPUs |
| `--gpu-counts LIST` | Output counts over the first N selected GPUs; default 1 through selected count; launches no additional searches |
| `--memory-budget FRACTION` | Fraction of each GPU's total memory; 0.9 |
| `--search-limit N` | Per-GPU search ceiling; 1024; extrapolated global batches may exceed it |
| `--trial-timeout SECONDS` | Deadline for each fresh trial group; 300 |
| `--refresh` | Replace completed compatible cases with fresh measurements |

Each output count uses the first N GPUs in the selected order. For example,
`--devices 2,0,1 --gpu-counts 1,3` reports allocations `(2)` and `(2,0,1)`.
If those GPUs have identical names and capacities, one single-GPU search supplies
both recommendations. A heterogeneous selection needs a compatible single-GPU
measurement for every distinct name/capacity group. No distributed probe or
multi-GPU confirmation is launched.

## Search and evidence

Before launching YOLO workers, the estimator persists an absolute Ultralytics
`weights_dir` and synchronizes the current process's native cache constant.
Relative directories are anchored to the estimator invocation cwd; existing
absolute directories are retained. Workers keep their trial directories while
finding selected and auxiliary AMP weights in that cache. For older prepared
caches, rerun `cy-download-weights` once from the original preparation directory;
see [cache setup and recovery](model-assets.md#cache-locations).

The public training batch is the **global microbatch across all training GPUs**.
Every estimator trial uses exactly one GPU, so its measured global and per-GPU
batches are equal. Search grows exponentially, refines the boundary by binary
search, and confirms the selected batch in a fresh supervised process.
Each trial performs five warm-up optimizer updates and ten measured updates,
including native loss/backward, optimizer state, configured EMA and bounded validation.
Native mixed precision and compilation settings remain part of the measured recipe.
The memory budget includes the idle device baseline and observed native CUDA
allocations outside the tensor allocator, alongside allocator peaks and whole-device
telemetry. It applies separately to every GPU.

Trials use the largest effective training resolution, including native multiscale
behavior. YOLO `optimizer=auto` measures both supported resolved optimizer paths
and retains the smaller validated capacity. Multi-GPU recommendations are derived
without additional trials and explicitly labelled `extrapolated`:

- Identical hardware: `global_batch = N × measured_per_gpu_batch`.
- Mixed hardware: `global_batch = N × min(compatible_per_gpu_capacities)`.

Both formulas produce a global batch divisible by N. Missing compatible evidence
for any GPU type/capacity prevents extrapolation. These recommendations are not
measured multi-GPU maxima. Exact lookup and extrapolation preserve source limitations:
`numerically_limited` takes precedence over `ceiling_limited`, which takes precedence
over `validated`. Neither lookup nor extrapolation establishes a missing capacity
boundary; source diagnostics remain part of the recommendation.

Confirmed CUDA allocation failure and exceeding the per-GPU memory budget bound
capacity. Timeout, rank crash, nonfinite computation, missing assets and interference
from another workload are distinct failures. The supervisor terminates only its own
workers. During discovery only, nonfinite computation after a fully successful,
under-budget candidate schedules one fresh confirmation of that last good batch.
A complete successful confirmation, including every required optimizer path,
validation and memory check, yields a usable `numerically_limited` result. The
failed numerical trial and its diagnostic remain in the evidence. The numerical
failure is never OOM or a memory upper bound; the result does not establish a
capacity maximum. A numerical failure before any successful candidate, any failed
confirmation (including nonfinite, OOM, memory-budget excess or timeout), or another
failure remains unusable. Recovery does not retry a failed confirmation.

A failed case has no usable recommendation; a nonzero command status can
coexist with completed results for other cases.

`validated` records a confirmed capacity boundary. `ceiling_limited` records a
confirmed batch at the requested ceiling and remains usable, but does not claim
an unconstrained maximum. `numerically_limited` records the independently repeated
last good batch after discovery stopped numerically, with no capacity maximum claim.
`no_capacity` and `failed` results retain diagnostics.
Even a validated batch is a recommendation for the recorded synthetic workload
and recipe, not a guarantee for arbitrary datasets or concurrent GPU use.

## Saved results and reuse

Results live in `CY_HOME/.config/clearml-yolo/batch-estimates.json`; `CY_HOME`
defaults to the launch working directory. The versioned JSON records global and
per-GPU batches separately, trial outcomes, synthetic limits and provenance.
Stored trial evidence is unchanged: extrapolations are derived during lookup and
reporting, never saved as manufactured measurements. Legacy measured allocations
remain readable. Schema 1 remains readable; ordinary saves write schema 2, which
supports `numerically_limited`. Upgrade older CY readers before sharing a schema-2
catalogue with them. Read-only access does not migrate or rewrite existing files.
Historical failed cases remain intact; inspect the new case matching the current
implementation and dependency versions after rerunning.
Updates use a native file lock and atomic replacement. A malformed catalogue is
reported as corruption and is not silently overwritten or treated as an empty cache.

Rerunning the same request reuses completed compatible cases. Failed or interrupted
cases are retried. `--refresh` invalidates each old matching success before probing
it again, so an interrupted refresh cannot leave a success that appears fresh.
Preserve the catalogue when investigating failures. Progress snapshots deliberately
retain status `failed` and null batch values until independent confirmation succeeds.
Their pending-confirmation diagnostic means the search may still be running or may
have been interrupted; the snapshot is never usable training evidence.

After upgrading, rerun failed cases. The changed implementation fingerprint makes
older measurements incompatible with the new recipe; use fresh measurements rather
than editing catalogue versions, statuses or trial records.

Compatibility covers architecture, nominal/effective resolution, GPU types and
capacities, relevant dependency and implementation versions, precision, compilation,
optimizers, accumulation, EMA and augmentation profile. Lookup first prefers a
compatible existing measurement for the exact ordered allocation and GPU count.
Otherwise it requires compatible single-GPU evidence for every hardware group and
derives the recommendation for the target count. Stale, failed and incompatible
sources cannot supply it. GPU UUIDs retain provenance without preventing reuse on
otherwise matching hardware.

## Select an estimate during training

Numeric defaults remain unchanged. Only explicit `batch=null` enables saved lookup:

```bash
cy-train ground_truth=./ground_truth.csv ultralytics.model=yolo11n.pt \
  ultralytics.imgsz=960 ultralytics.device=0 ultralytics.batch=null \
  clearml.project_name=detection clearml.task_name=yolo-estimated 'clearml.tags=[training]'

cy-train model=fcos/resnet50_fpn ground_truth=./ground_truth.csv \
  model.train.imgsz=960 model.train.device=0 model.train.batch=null \
  clearml.project_name=detection clearml.task_name=fcos-estimated 'clearml.tags=[training]'
```

Lookup runs after actual device selection and dataset preparation, before native
training. The dataset's foreground vocabulary and maximum object count on any
training or validation image must fit inside the saved synthetic bounds. Average
object density is insufficient. A missing/incompatible result stops with an
estimator command and the alternative of setting an explicit batch.

The requested null stays in canonical replay configuration. The resolved batch and
recommendation provenance are recorded separately as `training_batch_estimate`:
measured/extrapolated origin, target allocation, source estimate keys, global and
per-GPU batches, source boundary/ceiling/numerical status and retained diagnostics.
Effective native arguments contain the chosen value. Queue submission preserves
null; the executing worker uses its assigned GPUs and accessible `CY_HOME` catalogue.
Run estimation on matching idle hardware before submission; queue submission does
not measure capacity.

Prediction batches retain their existing controls. Explicit positive batches and
YOLO's existing AutoBatch values retain their behavior. CPU/MPS, custom augmentation,
non-square lookup requests and unsupported/custom model profiles require an explicit
batch when the standard estimator cannot supply matching evidence. Training keeps
its normal failure behavior: an OOM does not trigger an automatic retry or hidden
batch reduction. This utility does not reserve GPUs or replace the [queue](queue.md).

## Numerical-search recovery on older versions

Older versions abort discovery on any nonfinite result, even after smaller batches
passed. For a workload already observed to pass at batch 24 with YOLOv3u, square
960 images, 100 classes and 300 objects/image, a bounded retry is:

```bash
cy-batch-estimate --imgsz 960 --classes 100 --objects-per-image 300 \
  --models ultralytics/yolov3u --search-limit 24
```

Use the same `CY_HOME` and selected devices as the intended training run. This
requests a new search and independent confirmation at the lower ceiling; earlier
success alone is insufficient. Batch 24 is a workload-specific example, not a
general hardware recommendation. A confirmed result is `ceiling_limited`. Upgrade
and rerun failed cases to use numerical recovery. Neither approach fixes or
identifies the underlying native numerical cause; changing AMP, optimizer paths
or finite checks to hide it is not part of this recovery.
