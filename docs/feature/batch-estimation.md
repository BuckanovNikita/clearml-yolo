# Batch estimation

`cy-batch-estimate` measures how many training images per GPU fit on the local hardware
and writes the result into an editable batch-size table. Training reads that table only
when its batch is explicitly unset (`ultralytics.batch=null` or `model.train.batch=null`);
numeric batches, defaults and YOLO AutoBatch values are used as given. Measurement runs
locally on synthetic data, creates no ClearML task, and searches each distinct GPU model
once in its own supervised process, so the table can then be edited by hand.

## Behavior

### Measurement

- Each case measures one model at one square size on one GPU. GPUs with the same name and
  total memory share a case; identical GPUs run different cases concurrently, and a GPU
  holds at most one case until its process and owned descendants exit. A GPU whose case
  cleanup cannot be verified is not reused in that invocation. Each case sees only its
  GPU, pinned by UUID through `CUDA_VISIBLE_DEVICES`. Candidates and optimizer
  paths inside a case run one after another, each in a fresh supervised process.
- The workload is fixed: 150 synthetic classes and `--objects-per-image` targets per image.
- The catalogue holds the standard pretrained YOLO detection checkpoints and every native
  preset from [detector families](detector-families.md). YOLO aliases such as `yolo11n.pt`
  or `yolo11n` resolve to `ultralytics/yolo11n`.
- Without `--models` or `--refresh`, existing exact table entries are kept and only
  missing combinations are measured; a saved confirmed measurement with an identical
  identity fills a missing entry without remeasuring. `--models` and `--refresh` always
  measure afresh.
- A busy GPU outside the run is neither stopped nor waited on: its case fails unless an
  identical GPU of this run becomes free. One case's failure does not stop other cases;
  unsafe process supervision stops the invocation, and cases already accepted stay
  published in the table and the measurement record.
- `--gpu-counts` reports recommendations for the first N GPUs in `--devices` order from
  single-GPU results; it launches no distributed measurement.

### Search

- New searches use strategy `memory_guided_small_batches_v1`. The first candidate is 8,
  or the ceiling when it is below 8. If 8 does not fit, integer batches 1–7 are
  binary-searched. Above 8 candidates stay on multiples of 8 and the ceiling rounds down.
- After two successful candidates, the next one is predicted from their memory peaks,
  capped at four times the last success and at the ceiling; flat or decreasing growth
  doubles instead. Only an observed CUDA OOM or budget excess bounds capacity.
- Every winner is confirmed again in a fresh process.

### Trials and memory

- A trial runs five warm-up and ten measured optimizer updates with native loss and
  backward, optimizer state, configured EMA and a bounded validation pass, using native
  mixed precision and compilation at the largest effective resolution including native
  multiscale. YOLO `optimizer=auto` measures AdamW and MuSGD and keeps the smaller result.
- The budget is `--memory-budget` times total GPU memory. Usage combines the allocator
  peak with the larger of the idle-device baseline and non-allocator memory, checked
  against whole-device telemetry. Foreign compute processes on the GPU contaminate a trial.
- Programmatic callers may require a free-memory reserve (`minimum_free_memory_bytes`,
  default 0). It is checked before launch and throughout the trial; a breach fails the
  trial as contamination, never as a capacity bound.
- Before YOLO trials, Ultralytics `weights_dir` is persisted as an absolute path so workers
  share one weight cache; see [model assets](model-assets.md).

### Outcomes

| Status | Meaning |
| --- | --- |
| `validated` | Confirmed boundary on the search grid |
| `ceiling_limited` | Confirmed at the search ceiling; true capacity may be higher |
| `numerically_limited` | Non-finite step after a success; last good batch confirmed once, no capacity claim |
| `no_capacity` | OOM or budget excess at batch one |
| `failed` | Timeout, crash, missing asset, contamination, cancellation, failed confirmation or infrastructure error |

No failed confirmation is retried. Telemetry and cleanup failures are errors, never
capacity evidence.

### Output

- Lines follow the requested model and GPU-count order, tab-separated:
  `<model> gpus=N global_batch=G per_gpu_batch=P table digest=<sha256> sources=<label>:
  <batch> (<origin>; …)`, plus `cached` when nothing was remeasured and
  `forced/background-sensitive` for forced sources. A count without an entry prints
  `<model> gpus=N unavailable <reason>`; an unusable case prints `<model> gpus=1
  <status> <diagnostic>`; numerically limited or forced cases add a `Measurement:` line.
  Fallback warnings go to stderr. The last line is `Results: <table>; evidence: <json>`.
- `--list` prints `MODEL STATUS REASON CONTEXT` rows with `covered`, `no_capacity`,
  `failed` or `not_attempted`, then `Summary: selected=… covered=… missing=…` and
  `Results: <table>`. It needs no CUDA and writes nothing. Control characters are escaped.

### Editable table

The training table is `CY_HOME/.config/clearml-yolo/batch-sizes.yaml` (`CY_HOME` defaults
to the launch directory), keyed by GPU label, square image size and canonical model, with
positive per-GPU batches:

```yaml
"NVIDIA GeForce RTX 4090 [24 GiB]":
  960:
    ultralytics/yolo11n: 32
    rfdetr/small: 3
```

- Labels read `Name [N GiB]`. Precise measured capacities live in a reserved
  `# clearml-yolo-batch-metadata:` comment line; keep it when editing. Entries without
  metadata are read literally.
- An entry changes only after the parent accepts a matching worker receipt, successful
  exit and owned-process cleanup. Fresh results replace it; competing results keep the
  smaller batch.
- Confirmed `no_capacity` removes the exact entry and records a failure marker that
  blocks fallback for that GPU, model and size; a later success clears it, and a manual
  exact entry overrides it. Timeouts, cancellation and other failures change nothing.
- Updates take a native file lock and replace the file atomically, keeping comments and
  unrelated entries.

### Training lookup

For each selected GPU, after device selection and dataset preparation:

1. use the exact GPU name and capacity entry for the model and size;
2. otherwise use an entry from a GPU with equal or less memory, preferring the largest
   capacity, then the smallest batch, then the GPU name;
3. set the global batch to the GPU count times the smallest per-GPU batch.

A fallback warns with its source and the command to measure the target. Class count,
object density, recipe, augmentation and dependency versions do not gate lookup. The
canonical run keeps `batch: null`; effective arguments hold the global batch and an
explicit device list, and the task records `training_batch_estimate` with the table
digest, target GPUs, selected entries, fallback flags and batches. With
`model.train.device=null`, lookup uses GPU 0. Lookup reads the GPUs visible to the
executing process, so a queue worker or ClearML Agent resolves `batch=null` against its
assigned GPUs and its own `CY_HOME` table; queue submission never measures or fills in a
batch, and Agent replay of a null request ignores the batch recorded in `General`.

### Internal measurement record

`CY_HOME/.config/clearml-yolo/batch-estimates.json` keeps detailed evidence. Reuse
requires an identical identity: architecture, nominal and effective size, GPU name and
capacity, workload, dependency versions, implementation, precision, compilation,
optimizers, accumulation, EMA, augmentation and search settings; GPU UUIDs are
provenance. Saves write schema 3; schemas 1 and 2 are read without rewriting. A case
stays `failed` with null batches until the parent accepts it. Training never reads it.

## Configuration

| Option | Default and meaning |
| --- | --- |
| `--imgsz N` | Required positive square size, except with `--list` |
| `--objects-per-image N` | 300 synthetic targets per image |
| `--models LIST` | All catalogue models; explicit models are measured afresh |
| `--devices LIST` | All visible GPUs; logical indexes inside `CUDA_VISIBLE_DEVICES` |
| `--jobs N` | Number of selected GPUs; maximum concurrent cases, `1` serializes |
| `--gpu-counts LIST` | 1 through the selected count |
| `--memory-budget FRACTION` | 0.9 of total GPU memory |
| `--search-limit N` | 1024 per GPU; ceilings below 8 are supported |
| `--trial-timeout SECONDS` | 300 per fresh trial |
| `--refresh` | Remeasure every selected combination |
| `--force` | Accept GPU activity without attributable compute processes |
| `--list` | Offline table coverage; accepts only `--models` |

`--force` keeps memory accounting, identity checks and confirmation, still rejects
foreign compute PIDs and missing telemetry, and stores results under distinct keys.

```bash
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn --devices 0,1
cy-batch-estimate --list --models yolo11n.pt,rfdetr/small
```

## Failure behavior

- Exit 1 when any case is unusable or a requested GPU count has no recommendation; exit 2
  for invalid arguments, malformed or unreadable table or evidence files and runtime
  errors. Missing `--list` entries are not an error; measurement flags with `--list` fail
  with `<flag> cannot be used with --list`.
- `batch=null` fails with `batch=null requires CUDA estimates; set an explicit batch for
  CPU/MPS`, `Non-square training requires an explicit batch`, `Custom YOLO architectures
  require an explicit batch`, or `No training batch table entry: … Run cy-batch-estimate
  … or set an explicit training batch.` when no entry applies or a marker blocks fallback.
  A selected index that is not visible fails with `Training device is outside the current
  CUDA visibility`.
- Measurement and `batch=null` lookup need `nvidia-smi` telemetry for every visible GPU:
  `Batch estimation requires nvidia-smi GPU telemetry`, `Visible CUDA device lacks
  whole-GPU telemetry (MIG unsupported)` and `No visible CUDA GPUs; batch estimation
  requires idle GPUs`. A GPU with foreign compute processes at launch fails the case with
  `No idle selected GPU for <name>: GPU <N> is busy or its telemetry is unavailable`;
  foreign compute that appears during a trial fails it as contamination (`GPU <N>
  measurement contaminated …`).
- Malformed YAML, duplicate keys, non-canonical models and non-positive batches fail
  without overwriting the table. Unknown strategies and schema-3 cases without one fail.
- Training OOM with a looked-up batch fails normally, without retry or reduction.

## Limits

- Measurements use one GPU, a synthetic workload and the default recipe; they guarantee
  nothing for arbitrary datasets or recipes. Multi-GPU batches extrapolate single-GPU
  entries. A fallback or manual entry is never a measurement on the target GPU.
- Forced results reflect recorded background activity, not an uncontended maximum.
- Programmatic probes may add a native model configuration, YOLO arguments and a resolved
  augmentation snapshot; the CLI uses the default recipe. YOLO probe recipes must keep the
  selected catalogue architecture and its pretrained asset. Changed `pretrained`,
  `distill_model`, `resume`, `single_cls`, `quantize`, `classes`, `task`, `cls_pw`,
  `freeze`, disabled `channels_last` or native `augmentations` fail with `YOLO batch
  measurement does not support the requested controls: …`. A custom pipeline must keep
  the measured input shape.

## Code and tests

- [core/batch_estimation.py](../../src/clearml_yolo/core/batch_estimation.py),
  [core/batch_sizes.py](../../src/clearml_yolo/core/batch_sizes.py) — search and table.
- [entrypoints/batch_estimate.py](../../src/clearml_yolo/entrypoints/batch_estimate.py),
  [batch_probe.py](../../src/clearml_yolo/adapters/integrations/batch_probe.py),
  [batch_resolution.py](../../src/clearml_yolo/adapters/integrations/batch_resolution.py),
  [storage/batch_sizes.py](../../src/clearml_yolo/adapters/storage/batch_sizes.py) — CLI,
  trials, training lookup and storage.
- Tests: [test_batch_search_strategy.py](../../tests/test_batch_search_strategy.py),
  [test_batch_sizes.py](../../tests/test_batch_sizes.py),
  [test_batch_resolution.py](../../tests/test_batch_resolution.py),
  [test_batch_estimate_cli.py](../../tests/test_batch_estimate_cli.py),
  [test_batch_estimate_list.py](../../tests/test_batch_estimate_list.py),
  [test_batch_probe.py](../../tests/test_batch_probe.py).
- Verification limits: unit tests use injected probes; real GPU capacity is established
  only by live native measurements.
