# Queue

`cy-queue` is a separate package that schedules CY `pipeline` and `train` runs on whole
NVIDIA GPUs for several Unix users on one or more hosts. It stores jobs durably, runs each
user's jobs under that user's own worker, reserves GPUs, supervises every job with a
guardian process, and offers cancellation, recovery, ordering and a terminal UI. CY never
imports the queue, and direct commands and externally managed ClearML Agents need neither
its installation nor its configuration. This file describes the contract CY provides to
the queue and the minimum an operator needs; the queue's own documentation lives in its
repository.

## Behavior

### Package boundary

- Dependency direction is `cy-queue` → `clearml-yolo`. The queue owns scheduling policy,
  durable records, GPU inventory (NVML), guardians, the CLI and TUI (Textual), and
  submission composition.
- CY owns what the queue reuses: process supervision, the invocation lifecycle channel,
  the runtime bootstrap and path validation, diagnostics, tracing, redaction, readable
  presentation, the Hydra configurations, validation and sweep helpers, and the `cy` and
  `cy-train` entrypoints that a job finally executes (see Code and tests).
- The queue declares a minimum compatible CY version in its package metadata; the
  paired check verifies the installed pair. A newer queue interface requires raising that
  minimum.

### How a queued job runs

1. `cy-queue submit` composes the `pipeline` (default) or `train` configuration with CY's
   configuration store and validation, expands and validates the complete Hydra sweep
   before any job is written, and freezes each job in an owner-private snapshot. The
   snapshot records resolved settings, project and working directory, interpreter,
   installed package and environment identity, and the requested GPUs.
2. A worker of the job's owner checks the frozen interpreter with CY's
   process-supervision probe and admits the job. A same-user guardian, a Linux
   subreaper, checks its own supervision support, reserves the GPUs, records its identity
   and claim, repeats the memory check and only then opens the launch gate.
3. The job process enters the recorded working directory (where the ordinary Git
   workspace warning then checks) and execs the existing CY entrypoint with
   `CUDA_VISIBLE_DEVICES` set to the allocation, the guardian's owner marker, an
   inherited local lifecycle channel and a progress file path. CY detects the channel and
   does not run its own descendant cleanup: the guardian owns cleanup and capacity, while
   CY still owns the ClearML task, required publication and the computation outcome.
4. A pipeline with training holds its full allocation during training. After training
   returns and unused model memory is released, CY sends one training-finished
   notification and waits up to 30 seconds for the acknowledgement. The guardian durably
   shrinks the claim to the first allocated GPU, releases the other GPUs and updates the
   public allocation before acknowledging. Prediction, metrics and comparison then run on
   that first GPU while other jobs may use the released ones.
5. `cy-train`, pipelines with `skip_train=true` and runs that fail before the
   notification never notify, so they keep the full allocation until they exit.
6. CY finalizes the ClearML task itself. A successful task may complete before the
   guardian finishes cleanup. The guardian releases the remaining claim only after
   verifying that all descendants exited.

### Training handoff failures

After training succeeds, every pipeline runs a `training_resources` stage that releases
unused training memory and, under the queue, sends the notification. If the release, the
notification or the acknowledgement fails, the pipeline records `training_resources` as
failed and skips prediction, metrics, comparison, report and
visualization with the reason
`Post-training resource transition failed; compute admission unknown`. Because training
already succeeded, the pipeline ends with warning completion and records this in
`pipeline_outcome.json`. GPUs released by a durable shrink are never restored; cleanup and
recovery use the remaining claim.

### Cancellation and recovery

- `cy-queue cancel JOB` by the owner signals the verified job process and gives it up to
  90 seconds, while keeping the allocation, to clean its workers and finish publication.
  Then the guardian applies CY's bounded TERM/KILL cleanup to every remaining descendant.
  Descendants born during the grace period are recorded; repeated cancellation does not
  reset the deadline. Forced termination may leave publication incomplete; local logs are
  kept.
- Guardian death or unverifiable cleanup makes the job `recovery_required` and keeps its
  evidence. Its current reservations stay exclusive, but stale unlocked records alone do
  not block admission. A completed successful ClearML task is not marked failed.
- Only the owner runs `cy-queue recover JOB`. Recovery searches globally for marked
  processes; inaccessible or ambiguous evidence keeps the job blocked, and an empty result
  must be stable across two scans. Uncertain jobs are never retried automatically.
- A worker exit never releases active reservations; guardians keep supervising.

### Job and reservation states

- Job: `pending` → `starting` → `running` → `completed`, `failed`, `cancelled` or
  `recovery_required`; owner cancellation turns a pending job into `cancelled` at once and
  a starting or running job into `cancelling` until the guardian finishes. On a
  `recovery_required` job, cancellation is recorded and takes effect through recovery.
  Missing or high GPU memory at launch returns a starting job to pending.
- A GPU reservation is taken atomically with fresh admission and released by acknowledged
  contraction or verified cleanup. `gpu free` advances the GPU's reservation generation,
  so an older guardian cannot recreate, overwrite or clear newer state.
- Archive and restore change visibility only; `recovery_required` jobs stay in the main
  view.

### Admission

- The earliest runnable job on each host runs first. Jobs whose owner has no live worker
  or whose request lacks a complete eligible set of GPUs are skipped. One worker per owner
  and queue root can run several jobs on disjoint GPUs. Running jobs are never moved or
  preempted.
- A GPU is automatically available only when its used memory is strictly below
  `queue.max_used_memory_gib` (default 2.0 GiB); equality is busy and missing telemetry is
  unavailable. The worker freezes the threshold into each guardian, which checks again
  right before launch. Process lists and utilization are not considered. Current
  reservations and explicit holds stay exclusive regardless of memory.
- The threshold concerns memory already in use, not whether the selected model, batch or
  compilation fits.

### Inventory, holds and manual freeing

- Inventory uses NVML and a metadata-only CUDA visibility probe. Unknown telemetry for a
  required device, visible MIG devices and damaged coordination state fail closed.
- `gpu disable N` adds the caller's hold, which blocks new allocations across queue roots
  on that host; `gpu enable N` removes only the caller's hold.
- `gpu free N` and its alias `gpu release N` immediately clear every reservation and hold
  on that one GPU across roots. They need no token, reason, flag or confirmation, perform
  no memory or process check, send no signal, leave other GPUs of the same allocation
  reserved and do not change any job outcome. The next job still needs fresh admission.
- GPU commands use physical `nvidia-smi` indexes, independent of `CUDA_VISIBLE_DEVICES`;
  `submit --devices` uses CUDA-visible logical order, resolved to physical GPUs at
  submission. Absent devices get word aliases, which are also valid selectors.

### Public summaries and logs

- `cy-queue list` and the TUI show owner, order, state, requested and allotted GPUs, wait
  reason, progress and a readable ClearML task link, never the private configuration.
  Jobs display as `Job 17 · <name>` and have stable `job-N` references from the durable
  submission sequence (raw job identifiers are also accepted); `submit --label` sets the
  name, which otherwise is the configured ClearML task name. In the TUI, `o` opens the
  selected job's task.
- Text output uses physical GPU indexes or aliases; full GPU UUIDs and claim tokens stay
  internal. `--json` adds machine identifiers for scripts.
- A job whose snapshot or status cannot be read stays listed as
  `Status unavailable; showing last recorded state`; JSON adds `warning_count` and
  `refresh_issues`.
- Job stdout and stderr go to `<project>/.cy/queue-logs/JOB_ID.log`, owner-only; while
  CY's console capture runs it receives the readable mirror, so exact bytes come from the
  project-local capture ([diagnostics](diagnostics.md)). CY writes
  the job's progress to `<project>/.cy/queue-status/JOB_ID.json`: the latest `progress`
  text, the training `iteration` and the `task_url`; the queue shows `progress` and the
  task link. Workers log state changes and a 60-second heartbeat to stderr, failed and
  `recovery_required` jobs at ERROR; `worker --log-level` selects `DEBUG`, `INFO`,
  `WARNING` or `ERROR`. Command results and `--json` output go to stdout.

### Operating the queue

```bash
cy-queue submit --gpus 2 -- --config-dir cy-config --config-name cy
cy-queue submit --command train --gpus 1 -- --config-dir train-config --config-name cy-train
cy-queue submit --devices 0,2 -- --config-dir cy-config --config-name cy
cy-queue submit --gpus 1 -- -m --config-dir cy-config --config-name cy \
  ultralytics.cls=0.25,0.5,1.0 ultralytics.cls_pw=0.0,0.5,1.0
cy-queue worker
cy-queue list --json
cy-queue move job-17 top --revision REVISION
```

- Everything after `--` is a Hydra override, `-m`, `--config-dir` or `--config-name`.
  Generate a `train` configuration with `cy-init-config DIR --command cy-train`.
- A sweep (`-m`, or a saved `hydra.mode=MULTIRUN`) becomes one job per combination, each
  with the requested GPUs; the example above creates nine one-GPU jobs. All jobs share
  one fresh multirun tag (see [commands and configuration](commands-and-configuration.md)).
- Every submission needs exactly one of `--gpus N` or `--devices LIST`; there is no
  default. Every job needs at least one whole GPU. A multi-GPU training job uses one rank
  per GPU; its global batch must be divisible by the GPU count. Explicit `batch=null` is
  resolved by the worker against its assigned GPUs (see [batch estimation](batch-estimation.md)).
- Leave native GPU `device` settings unset; the allocation supplies them. Explicit CPU
  phases stay on CPU. Compilation, AMP, batch and model settings are kept.
- Submission downloads nothing. Dataset availability, model loading and memory fit are
  execution-time checks; an unversioned ClearML dataset selector resolves when the job
  runs (see [datasets and ground truth](datasets-and-ground-truth.md)).
- Submission freezes the configuration: later YAML edits do not affect submitted jobs.
  Changing either package or the environment makes pending jobs fail identity checks;
  cancel and resubmit them.
- `move` (`up`, `down`, `top`, `bottom`, `before JOB`, `after JOB`) needs the current
  revision from `list --json`. Any local user may reorder pending jobs; only the owner may
  `cancel`, `recover`, `archive` (completed, failed or cancelled jobs) or `restore`.
- `cy-queue tui` offers the same operations; closing it leaves workers running.
- For a stuck job, inspect the wait reason, the owner's worker and the guardian state.
  Never delete live lock or recovery files, and never treat a vanished PID or record age
  as proof of cleanup.

## Configuration

### Installation

Install CY from source with its approved external dependencies (see
[installation](installation.md)), then install `cy-queue` into the same environment. From
a CY checkout with a sibling `cy-queue` checkout:

```bash
git clone https://github.com/BuckanovNikita/cy-queue.git ../cy-queue
uv sync --frozen --inexact
uv pip install --python .venv/bin/python -e . -e ../cy-queue
uv pip check --python .venv/bin/python
uv run --frozen --no-sync cy-queue --help
```

Run ad hoc commands in this environment with `uv run --frozen --no-sync` so that a sync
never removes the separately installed queue. Textual and NVML are dependencies of
`cy-queue`, not of CY. Before upgrading a shared queue, stop submissions and all workers,
let guardians finish or recover their jobs, upgrade every participant together and
resubmit pending jobs; never run old and new workers at the same time.

### Queue settings

Every queue command except help needs a TOML file:
`$XDG_CONFIG_HOME/clearml-yolo/queue.toml`, or `~/.config/clearml-yolo/queue.toml` when
`XDG_CONFIG_HOME` is unset, empty or relative. `CY_QUEUE_CONFIG` overrides it and must be
absolute. Nothing is created automatically.

```toml
[queue]
name = "Team training"
root = "/srv/clearml-yolo/queue"
coordination_root = "/var/lib/clearml-yolo/coordination"
max_used_memory_gib = 2.0
```

- `name` (non-empty printable text), `root` (shared job metadata) and
  `coordination_root` (locks, reservations, worker registrations and recovery evidence)
  are required; both roots are absolute paths, identical for all users of a queue.
  Neither derives from `CY_HOME`; a newly created root gets mode `1777`, while existing
  roots keep theirs.
- `max_used_memory_gib` is optional, a positive finite number; strings, booleans, zero,
  negative and non-finite values are rejected. There is no worker flag for it. Restart
  the worker to apply a change; running guardians keep their frozen value.
- `cy-queue config [--json]` validates and shows the effective settings without creating
  anything. `--root` overrides only the metadata root; a legacy `CY_QUEUE_ROOT` must
  agree with it.
- One coordination root is bound per host under `/tmp/clearml-yolo-queue`; its locks keep
  different queue roots on that host from reserving the same GPU. A conflicting
  configuration fails. Moving it is an offline administrator procedure.
- `root` may be on NFS with consistent UID mapping. `coordination_root` must be on a
  host-local Linux filesystem that supports `flock` or on an eligible NFS mount; other
  filesystems are rejected. An NFS `coordination_root` must be
  mounted `hard` with `local_lock=flock` or `local_lock=all` and shared cache; `soft`,
  `softerr`, `nosharecache` and remote locking are rejected. Each host needs a distinct
  machine identity, and all participants on a host must share its mount, PID namespace
  and bootstrap.

## Failure behavior

- Missing or incomplete settings fail before any queue directory or host binding is
  created.
- `--gpus 0`, combining `--gpus` with `--devices`, native GPU device overrides and
  `queue.*`, `autogpu.*`, `auto_gpu.*` or `hydra/launcher` overrides are rejected at
  submission.
- An interpreter without process-supervision support is rejected by the worker before the
  job leaves pending and again by the guardian before it reserves GPUs.
- A changed installation identity fails execution; pending jobs must be resubmitted.
- Unknown required-device telemetry, visible MIG, damaged coordination records and NFS
  failure stop new admission; active reservations stay protected.
- Monitoring never recovers jobs, changes outcomes or releases reservations.

## Limits

- Queued execution needs Linux with pidfd and subreaper support, cooperating Unix users
  and a shared host PID namespace. The package installs no privileged service and changes
  no mounts or accounts.
- Hard NFS mounts can block status, recovery and cleanup indefinitely during an outage;
  mount-option checks are an eligibility check, not a guarantee of locking behavior.
- Physical multi-GPU training, actual multi-user and multi-host NFS operation, and live
  ClearML publication from queued jobs are established only in those environments.
  Simulated telemetry and CPU tests establish state and process behavior only.

## Code and tests

- [adapters/runtime/execution_lifecycle.py](../../src/clearml_yolo/adapters/runtime/execution_lifecycle.py)
  — lifecycle channel and training-finished handoff.
- [adapters/runtime/process_tree.py](../../src/clearml_yolo/adapters/runtime/process_tree.py)
  — supervision used by guardians and recovery.
- [application/use_cases/pipeline.py](../../src/clearml_yolo/application/use_cases/pipeline.py)
  — the handoff stage and skip behavior after a failed handoff.
- [adapters/observability/capture.py](../../src/clearml_yolo/adapters/observability/capture.py)
  — the progress file.
- Tests: [test_execution_lifecycle.py](../../tests/test_execution_lifecycle.py),
  [test_process_capabilities.py](../../tests/test_process_capabilities.py),
  [test_subreaper_process_tree.py](../../tests/test_subreaper_process_tree.py),
  [test_execution_controls.py](../../tests/test_execution_controls.py).
- Scheduling, storage, guardian, admission and CLI behavior are tested in the
  `cy-queue` repository. Installing both packages together is verified by the paired
  release check in [development](../development.md).
