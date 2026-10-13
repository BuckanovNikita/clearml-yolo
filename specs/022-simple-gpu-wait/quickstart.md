# GPU execution quickstart

Install the project and supply explicit ClearML project/tags and project-local
credentials as described in the [README](../../README.md). Back up custom YAML
before regenerating examples; see [migration](../../docs/python-import-migration.md).

```bash
cy-init-config cy-config
cy --config-dir cy-config --config-name cy ultralytics.device=-1 ultralytics_predict.device=-1
```

Both controls default true: wait for FIFO admission, reserve free visible whole GPUs
and run a fresh supervised child. CUDA visibility determines available identities.
A GPU qualifies when total NVML used memory is strictly below 2 GiB (2048 MiB),
regardless of process presence. Equality is busy; reservations still exclude devices.
Set a project-wide limit in the exported command YAML:

```yaml
autogpu:
  enabled: true
  force: false
  max_used_memory_gib: 2.0
```

Override per invocation with `autogpu.max_used_memory_gib=1.5`. Use a finite positive
number. This also controls exact queued selection; fully disabled scheduling does
not probe GPUs. Run updated supervisors together so each uses its own project limit.
For example, 1215 MiB and 409 MiB both qualify under the default 2048 MiB cutoff.

CPU/MPS bypass scheduling. For native two-GPU DDP, Ultralytics launches its descendants:

```bash
cy --config-dir cy-config --config-name cy 'ultralytics.device=[-1,-1]' ultralytics_predict.device=-1
```

Automatic selection treats native IDs as demand. Training uses both assigned devices;
after native memory cleanup the reservation contracts to the inference device.
Requests larger than the supported visible set fail. Physical multi-GPU execution
must be reported unverified when not exercised.

Select direct availability waiting, exact queued selectors, or native pass-through:

```bash
cy --config-dir cy-config --config-name cy queue.enabled=false
cy --config-dir cy-config --config-name cy autogpu.enabled=false ultralytics.device=0 ultralytics_predict.device=0
cy --config-dir cy-config --config-name cy queue.enabled=false autogpu.enabled=false ultralytics.device=cpu ultralytics_predict.device=cpu
```

Exact queued selectors preserve physical identity within inherited visibility; automatic
selectors such as `-1` are rejected. Direct waiting gives no exclusive reservation.
Both controls false preserves native settings and bypasses project GPU discovery/waiting.

Queued local sweeps use the concurrent project launcher. Set `queue.enabled=false`
for a sequential BasicLauncher sweep; mixed queue modes fail before admission:

```bash
cy --multirun --config-dir cy-config --config-name cy queue.enabled=false ultralytics.device=cpu ultralytics_predict.device=cpu ultralytics.epochs=1,2
```

Each job preserves Hydra environment/output/chdir behavior and owns its task. Interrupting
admission creates no task; cancellation of active work waits for owned GPU process cleanup.
See the [execution contract](contracts/execution.md) for four modes, exact union,
replay and native owner rules.

## Force explicit devices

To start directly on five explicitly selected GPUs, bypassing project memory and
queue admission checks even while the enabled switches stay true:

```bash
cy --config-dir cy-config --config-name cy autogpu.force=true 'ultralytics.device=[0,1,2,3,4]' ultralytics_predict.device=0
```

Indexes are relative to inherited `CUDA_VISIBLE_DEVICES`; training keeps their order.
Provide concrete devices for every enabled GPU stage. CPU/MPS also work. Automatic
selectors (`-1`, null, empty, bare `cuda`) fail. ClearML tracking remains enabled and
replay cannot change forced devices. Forced sweeps are sequential; mixed effective
queued/unqueued sweeps fail before any job starts.

Ordinary waits explain each card and show requested/visible/eligible counts, the
memory threshold and queue position. For five of eight cards below the threshold,
an empty queue admits immediately; active reservations or FIFO can still delay it.
See [diagnostics](../../docs/diagnostics.md#gpu-admission-decisions) to interpret logs.
