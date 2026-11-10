# Batch estimation and editable training lookup

`cy-batch-estimate` measures single-GPU capacity locally without a ClearML task.
Only explicit training `batch=null` requests table lookup; numeric defaults and
explicit batches retain their existing behavior.

## Measure selected cases

```bash
cy-batch-estimate --imgsz 960
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn --devices 0,1
cy-batch-estimate --imgsz 960 --models yolo11n --search-limit 3 --jobs 1
```

Measurements always use **150 synthetic classes**. `--classes` is not supported.
The default catalogue contains the 44 standard pretrained YOLO detection variants
and all native presets in the [model guide](multi-model-backends.md). YOLO aliases
such as `yolo11n.pt` resolve to canonical `ultralytics/yolo11n`.

| Option | Meaning and default |
| --- | --- |
| `--imgsz N` | Required positive nominal square resolution, except with `--list` |
| `--objects-per-image N` | Positive target density for every image; 300 |
| `--models LIST` | Canonical presets or YOLO aliases; explicit selection always measures afresh |
| `--devices LIST` | Ordered logical indexes within inherited CUDA visibility; all visible GPUs |
| `--jobs N` | Maximum concurrent independent searches; default uses available selected GPUs |
| `--gpu-counts LIST` | Report over first N selected GPUs; default 1 through selected count; no extra searches |
| `--force` | Permit unattributed background activity, retaining telemetry and foreign-compute checks |
| `--memory-budget FRACTION` | Fraction of GPU total memory; 0.9 |
| `--search-limit N` | Positive per-GPU ceiling; 1024; ceilings below eight are supported |
| `--trial-timeout SECONDS` | Deadline per fresh trial group; 300 |
| `--refresh` | Remeasure every selected combination |

Without explicit `--models` or `--refresh`, preserve exact table entries and measure
missing model/size/hardware combinations. Compatible internal cached evidence may
populate missing entries. Cross-GPU fallback never counts as exact coverage.

Each distinct hardware name/capacity needs one single-GPU search per model. Identical
GPUs can run different cases concurrently; each GPU belongs to at most one case until
its worker and owned descendants exit. Candidates and optimizer paths within a case
remain sequential. Busy unrelated GPUs are neither stopped nor waited on indefinitely.
Ordinary case failures do not terminate peers; unsafe process supervision stops the
invocation. Output follows requested model/GPU-count order. Counts use the first N
GPUs in `--devices` order; they do not launch distributed confirmation.

## Search and evidence

New searches use `memory_guided_small_batches_v1`. Start at eight when the ceiling
permits, otherwise at the ceiling. If eight exceeds capacity, binary-search integer
batches one through seven. Above eight retain the multiples-of-eight grid and round
ceilings down to that grid. Only OOM or memory-budget excess at **batch one** yields
`no_capacity`. Every winner is independently confirmed in a fresh supervised process.

After the first successful candidates, predict from the last two measured memory
peaks, cap jumps at four times the last successful batch and at the ceiling, and
fall back to doubling for flat/decreasing growth. Predictions are candidates, never
capacity evidence. Only observed CUDA OOM or budget excess bounds the capacity search.

Each trial performs five warm-up and ten measured optimizer updates, native
loss/backward, optimizer state, configured EMA and bounded validation. Native mixed
precision and compilation remain part of the measured recipe. Use the largest effective
training resolution, including multiscale behavior. YOLO `optimizer=auto` measures
both supported resolved optimizer paths and retains the smaller confirmed capacity.
The budget includes the idle-device baseline, native CUDA allocations outside the
tensor allocator, allocator peaks and whole-device telemetry.

Before YOLO workers launch, persist an absolute Ultralytics `weights_dir` and synchronize
the current process cache constant. Relative paths are anchored to invocation cwd;
existing absolute paths remain. Workers retain trial directories and discover AMP and
selected weights in that cache. See [cache recovery](model-assets.md#cache-locations).

Discovery-time nonfinite computation after a successful under-budget candidate
schedules one independent confirmation of that last good batch. Success yields
`numerically_limited`, retaining the cause without claiming a capacity maximum.
Numerical failure before any success, any failed confirmation, timeout, crash, missing
assets, cancellation and infrastructure failures remain distinct unsuccessful outcomes.
No failed confirmation is retried. `validated` means a confirmed boundary on the search
grid; `ceiling_limited` means a confirmed ceiling, not an unconstrained maximum.

Telemetry-query and worker-cleanup failures are errors, never capacity evidence.
Diagnostics retain grouped causes, surviving descendants and relevant query output.
The supervisor terminates only owned processes. A GPU-specific idle/ownership rejection
is contamination. A recommendation cannot guarantee success for arbitrary workloads.

## Editable lookup table

The authoritative training table is `CY_HOME/.config/clearml-yolo/batch-sizes.yaml`;
`CY_HOME` defaults to the launch directory:

```yaml
"NVIDIA GeForce RTX 4090 [24 GiB]":
  960:
    ultralytics/yolo11n: 32
    rfdetr/small: 3
```

Values are **per-GPU batches**, accepting every positive integer. Keys identify
canonical model, square image size and hardware. Generated labels are readable GiB;
internal metadata retains precise memory bytes. Manually added capacities without
metadata are interpreted literally. Metadata is stored in a reserved JSON comment
so it and the public table change atomically. Preserve that comment when editing values.

Resolve each selected GPU separately:

1. Prefer exact GPU name and capacity for the model/size.
2. Otherwise choose an entry from any GPU with equal or lower VRAM, taking the
   largest eligible capacity. Break ties by smallest batch, then GPU name.
3. Compute global batch as GPU count times the smallest resolved per-GPU batch.

Fallback warns with the source and a command for measuring the current GPU. It is
not a measurement on that GPU. Class count, object density, training recipe,
augmentation and dependency versions do **not** gate table lookup.

## Publication, refresh and failure handling

Generated entries are published only after the parent accepts matching worker identity
and result, successful exit, and owned-process cleanup. Successful fresh measurement
replaces the selected entry; competing eligible results use the smallest confirmed
batch. Historical measurements cannot override fresh results.

Confirmed `no_capacity` removes the exact entry and records an internal failure marker
blocking fallback for that hardware/model/size. Successful remeasurement clears it.
A valid manually added exact entry overrides the marker. Timeout, cancellation and
infrastructure failure preserve existing table values and report an unsuccessful refresh.

Updates use native locking and atomic replacement, preserving comments and unrelated
entries. Malformed YAML, duplicate keys and invalid values fail without overwrite.
Read-only access does not migrate data.

## Internal measurement cache

Detailed evidence remains in `CY_HOME/.config/clearml-yolo/batch-estimates.json`.
It is separate from the training table; training never silently falls back to JSON.
Internal reuse still checks architecture, nominal/effective resolution, hardware,
workload, dependencies, implementation, precision, compilation, optimizers,
accumulation, EMA and augmentation. UUIDs retain provenance without gating reuse on
otherwise identical hardware.

Historical schemas and strategies retain their original trial replay and estimate
keys, including strategy-less exponential histories. Ordinary saves use schema 3
with explicit strategies. Unknown strategies, mismatched evidence and missing schema-3
strategies fail. Upgrade older readers before sharing new-strategy catalogues. Never
edit history to manufacture confirmation or round old values into unmeasured evidence.
Malformed JSON is reported without overwrite.

Progress snapshots retain failed status and null batches while confirmation or parent
acceptance is pending. Interrupted refresh may replace the matching JSON progress
record, but does not invalidate the existing editable table value. Keep diagnostics
when investigating failures. Pending status may describe an active or interrupted run.

## Inspect saved coverage without measuring

```bash
cy-batch-estimate --list
cy-batch-estimate --list --models yolo11n.pt,rfdetr/small
```

Listing reports table coverage and known failures, without CUDA discovery or probes.
It needs no image size and writes no table or runtime state. It does not prove capacity
on the current GPU. Missing entries are not an error. Malformed/unreadable data and
invalid arguments exit 2. Only listing, model filters and help are accepted together;
measurement flags are rejected. Stored control characters are escaped in output.

## Forced measurement with background activity

`--force` permits nonzero utilization and activity without attributable compute PIDs.
Some drivers omit competing compute processes, so this is not proof of graphics-only
activity. Explicit foreign compute PIDs and invalid/missing telemetry still reject a
case. Memory accounting, hardware identity, finite checks and confirmation remain.
No existing process is stopped. Forced evidence retains `settings.force` and distinct
keys; ordinary settings omit false to preserve old keys. Forced sources are
background-sensitive recommendations, not uncontended maxima.

## Select a table entry during training

```bash
cy-train ground_truth=./ground_truth.csv ultralytics.model=yolo11n.pt \
  ultralytics.imgsz=960 ultralytics.device=0 ultralytics.batch=null \
  clearml.project_name=detection clearml.task_name=yolo-estimated 'clearml.tags=[training]'

cy-train model=fcos/resnet50_fpn ground_truth=./ground_truth.csv \
  model.train.imgsz=960 model.train.device=0 model.train.batch=null \
  clearml.project_name=detection clearml.task_name=fcos-estimated 'clearml.tags=[training]'
```

Lookup occurs after device selection and dataset preparation, before training. Null
remains in canonical replay; effective native arguments contain the chosen global batch.
`training_batch_estimate` records table digest, target GPUs, selected entries, fallback
sources and resolved batches. Manual entries and fallback values are never presented
as measurements on the target. Queue workers resolve null against their assigned GPUs
and accessible `CY_HOME`; queue submission does not measure capacity.

CPU/MPS, unsupported/custom model identities and non-square requests require explicit
batches. Custom augmentation is not a lookup gate. Prediction controls, explicit positive
training batches and YOLO AutoBatch values retain their behavior. Training OOM fails
normally with no automatic retry or hidden reduction. Device assignment does not
reserve hardware against other programs or replace the [queue](queue.md).
