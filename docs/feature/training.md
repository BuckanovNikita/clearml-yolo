# Training

Training turns validated CSV ground truth into one native best checkpoint for the selected
detector family. `cy-train` runs it as a standalone command and `cy` runs it as the
pipeline's training stage. CY owns the experiment around the native trainer: it prepares
the dataset, resolves an unset batch, starts and supervises training processes on the
requested devices, keeps the ClearML task in the invocation owner and returns the selected
checkpoint for prediction, validation and publication.

## Behavior

### Native training ownership

- Ultralytics YOLO trains through its own trainer with settings from `ultralytics.*`;
  DEIMv2, RF-DETR, Faster R-CNN and FCOS train through their native trainers with settings
  from `model.train.*`. See [detector families](detector-families.md) for selection.
- Training requires `ground_truth` and nonempty `train` and `val` splits; `cy` also
  requires the splits its enabled later stages consume, including `test` for comparison.
  Dataset preparation is described in
  [datasets and ground truth](datasets-and-ground-truth.md).
- Every run starts a new training. YOLO `resume` is rejected with `resume is unsupported
  with ground_truth; use model weights to fine-tune`; native families never resume
  optimizer or scheduler state.
- The invocation owner holds the only ClearML task. Native training without an
  invocation-owned task fails with `Native training requires an invocation-owned ClearML
  task`. Training workers and DDP ranks never create tasks or upload artifacts.
- Requested and effective arguments are kept separately. YOLO writes
  `.configs/<name>/ultralytics_requested.yaml` under its project and `ultralytics.yaml` in
  the run directory, and records changed values as `training_normalization`. Native
  families write `native_train.yaml` in the run directory and record the effective
  arguments on the task.

### Devices

- Direct commands pass the configured device to the native trainer without queue
  admission, waiting or automatic substitution. Scheduled execution belongs to the
  [queue](queue.md).
- YOLO accepts any `ultralytics.device` value that Ultralytics accepts; several devices run
  Ultralytics' own DDP launcher.
- `model.train.device` accepts `null`, `cpu`, `cuda`, `cuda:N`, one index, a list such as
  `[0,1]` or a comma-separated string. `null` uses CUDA when available and CPU otherwise.
  Indexes are logical positions inside the inherited `CUDA_VISIBLE_DEVICES`.
- Two or more indexes start native multi-GPU training: one supervised process per GPU.
  DEIMv2 uses its native DDP over NCCL, RF-DETR uses Lightning DDP, and Faster R-CNN and
  FCOS use distributed sampling, accumulation-aware gradient synchronization, synchronized
  EMA and validation without padded duplicate samples. Each rank binds its CUDA device
  before building the model; DEIMv2, Faster R-CNN and FCOS ranks join an NCCL process
  group with a 120-second initialization timeout, and RF-DETR leaves that to Lightning.
- `model.train.batch` is the global microbatch across all ranks. It must be divisible by
  the number of GPUs; each rank trains on `batch / GPUs` images. `grad_accum_steps`
  multiplies the global microbatch into the effective optimizer batch.
- Prediction after training runs on a single device and takes its own
  `model.predict.device`. For a CPU `cy` run, set both `model.train.device=cpu` and
  `model.predict.device=cpu`.

### Training worker processes

- Native multi-GPU training keeps the invocation owner outside the ranks. The owner writes
  one typed request under `<run>/workers/<token>/`, starts one fresh rank process per GPU
  and streams each rank's console log to its own output while ranks run.
- Rank zero writes metric scalars and the aggregate checkpoint; the owner relays those
  scalars to the task live and publishes the result only after every rank returns a
  matching successful receipt.
- YOLO multi-GPU training uses CY's trainer class inside Ultralytics' fresh DDP
  interpreters. Rank zero journals its callback events in invocation scratch; ranks need no
  persisted ClearML settings. The owner's relay reads only those local records and, after
  training, replays them through the installed ClearML callbacks under a deadline, without
  duplicating scalars already relayed.

### Outcomes and checkpoints

Training succeeds only when the native run returns and its best checkpoint exists:

| Family | Best checkpoint | Selection |
| --- | --- | --- |
| YOLO | `weights/best.pt` | Native Ultralytics fitness |
| DEIMv2 | `best_stg2.pth`, else `best_stg1.pth` | Native stage-best checkpoint |
| RF-DETR | `checkpoint_best_total.pth` | Native best checkpoint |
| Faster R-CNN, FCOS | `best.pth` | Highest validation COCO mAP50–95 (`val/map50_95`) |

The owner publishes one best Output Model and records training counts for that checkpoint.
For YOLO, the log line `Training checkpoint: <path>` gives the checkpoint's exact location.
Native checkpoints carry an embedded descriptor described in
[detector families](detector-families.md). Inside `cy`, a nonempty trained checkpoint marks
training as succeeded even if later publication fails; see
[ClearML publication](clearml-publication.md).

## Configuration

Native families use these `model.train` keys; unknown keys are rejected.

| Key | Default | Meaning |
| --- | --- | --- |
| `epochs` | 100 | Positive number of epochs |
| `batch` | 4 | Global microbatch; `null` reads the [batch-size table](batch-estimation.md) |
| `workers` | 4 | Data-loading processes; 0 loads in the main process |
| `imgsz` | preset size | Positive integer or `[height,width]` |
| `device` | `null` | Device selection described under Devices |
| `lr`, `weight_decay` | 0.0001, 0.0001 | Optimizer learning rate and weight decay |
| `seed` | 0 | Native training seed |
| `pretrained`, `weights`, `backbone_weights` | `true`, `null`, `null` | Initialization; see [detector families](detector-families.md) |
| `amp`, `use_ema` | `true`, `true` | Mixed precision and exponential moving average |
| `grad_accum_steps` | 1 | Gradient accumulation; DEIMv2 accepts only 1 |
| `augmentation` | `null` | Custom-mode overrides; see [augmentation](augmentation.md) |

YOLO training uses `ultralytics.*` with the installed Ultralytics defaults plus project
defaults `model=yolo11n.pt`, `imgsz=960`, `compile=true` and `nms=true`. Pass device,
batch, AMP and compilation through that group, for example `ultralytics.epochs=20`. YOLO
AutoBatch values (`batch=-1` or a fraction) select the initial batch natively.
`ultralytics.batch=null` reads the batch-size table.

```bash
cy-train model=fasterrcnn/convnext_tiny ground_truth=./ground_truth.csv \
  model.train.epochs=20 'model.train.device=[0,1]' model.train.batch=8 \
  clearml.project_name=detection clearml.task_name=convnext-train \
  'clearml.tags=[fasterrcnn,experiment]'
```

## Failure behavior

- A non-finite scalar fails training with `Native scalar must be finite: title=…,
  series=…, iteration=…, value=…`. A non-finite Faster R-CNN or FCOS loss fails with
  `Torchvision training produced a nonfinite loss: batch=…, image_ids=…, losses=…`, naming
  the zero-based batch, target image IDs and each loss component.
- CY applies no automatic precision fallback and substitutes no value for a non-finite one.
  With YOLO `compile=true`, Ultralytics itself continues uncompiled with a warning when
  compilation cannot be set up; CY adds no compiler fallback of its own.
- A programmatic caller that passes a sparse YOLO mapping fails with `Missing ultralytics
  parameters [...]; compose a complete ultralytics group` (`ultralytics_predict` for
  prediction).
- An incomplete rank-zero event journal fails YOLO multi-GPU training with `Native DDP
  event output is incomplete: ...`.
- CUDA out-of-memory fails training. CY never retries with a smaller batch: Ultralytics'
  in-training OOM recovery is disabled once training batches start.
- A missing best checkpoint fails training, for example `Training finished without
  required checkpoint …` for YOLO.
- In multi-GPU training, a failed, timed-out or cancelled rank terminates the whole owned
  rank group and fails with `Native distributed training <status>: <diagnostics>`.
  Ranks that exit without matching successful receipts fail with `Native workers exited
  without matching successful receipts`.
- Duplicate or negative indexes fail with `Native training devices must be distinct
  nonnegative GPU indices`; an index outside `CUDA_VISIBLE_DEVICES` fails with `Training
  device is outside CUDA_VISIBLE_DEVICES`; an indivisible batch fails with `Global training
  batch must be positive and divisible by GPU count`.

## Limits

- Multi-GPU native training applies to DEIMv2, RF-DETR, Faster R-CNN and FCOS through CY's
  supervisor and to YOLO through Ultralytics. Prediction is single-device.
- MPS is not a supported cross-family training target; DEIMv2 and RF-DETR reject it.
- Family-specific size and accumulation limits, such as DEIMv2's `grad_accum_steps=1`
  and square training size, are listed in [detector families](detector-families.md).
- Multi-GPU worker supervision has a 30-day deadline.
- Device assignment does not reserve hardware against other programs.

## Code and tests

- [use_cases/train.py](../../src/clearml_yolo/application/use_cases/train.py) — CSV
  training workflow.
- [integrations/training.py](../../src/clearml_yolo/adapters/integrations/training.py),
  [native_trainer.py](../../src/clearml_yolo/adapters/integrations/native_trainer.py),
  [native_ddp.py](../../src/clearml_yolo/adapters/integrations/native_ddp.py) — YOLO
  training, owned trainer and DDP relay.
- [detectors.py](../../src/clearml_yolo/adapters/integrations/detectors.py),
  [distributed_training.py](../../src/clearml_yolo/adapters/integrations/distributed_training.py),
  [training_worker.py](../../src/clearml_yolo/adapters/integrations/training_worker.py),
  [runtime/workers.py](../../src/clearml_yolo/adapters/runtime/workers.py),
  [runtime/distributed.py](../../src/clearml_yolo/adapters/runtime/distributed.py) —
  native routing, rank supervision and device parsing.
- Tests: [test_train.py](../../tests/test_train.py),
  [test_training_workers.py](../../tests/test_training_workers.py),
  [test_distributed_training.py](../../tests/test_distributed_training.py),
  [test_distributed_configuration.py](../../tests/test_distributed_configuration.py),
  [test_torchvision_distributed.py](../../tests/test_torchvision_distributed.py),
  [test_native_ddp.py](../../tests/test_native_ddp.py),
  [test_native_ddp_cpu.py](../../tests/test_native_ddp_cpu.py),
  [test_native_training_outcomes.py](../../tests/test_native_training_outcomes.py),
  [test_yolo_oom.py](../../tests/test_yolo_oom.py).
- Verification limits: CPU/Gloo DDP tests establish rank supervision and owner relay only;
  NCCL, AMP and physical multi-GPU execution are established only by live GPU runs.
