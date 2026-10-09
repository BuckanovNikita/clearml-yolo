# Simple GPU waiting quickstart

Install the project and configure dataset paths and explicit ClearML project/tags
as described in the [README](../../README.md). Back up custom YAML before regenerating
existing examples; see [configuration migration](../../docs/python-import-migration.md).

```bash
cy-init-config cy-config
cy --config-dir cy-config --config-name cy ultralytics.device=-1 ultralytics_predict.device=-1
```

The command waits for enough free visible whole GPUs before creating its ClearML
task, then executes directly. If inherited `CUDA_VISIBLE_DEVICES` restricts or
reorders devices, selection follows that logical visibility order. Native GPU IDs
in device settings express demand; they do not pin a physical GPU. Availability
requires no other compute process; it does not measure a free-memory threshold.

For two-GPU native training, set a two-entry selector. Ultralytics launches DDP:

```bash
cy --config-dir cy-config --config-name cy 'ultralytics.device=[-1,-1]' ultralytics_predict.device=-1
```

Training uses two selected logical devices; downstream GPU inference uses the first.
A demand above the supported visible device count fails clearly. If physical multi-GPU
execution is unavailable, do not report it as verified. CPU execution bypasses NVML:

```bash
cy --config-dir cy-config --config-name cy ultralytics.device=cpu ultralytics_predict.device=cpu
```

A local sweep uses the standard sequential Hydra launcher. Choose suitable native
CPU options for the dataset and environment:

```bash
cy --multirun --config-dir cy-config --config-name cy ultralytics.device=cpu ultralytics_predict.device=cpu ultralytics.epochs=1,2
```

Each job retains Hydra environment/output/chdir behavior and its own task. There is
no queue, ticket, reservation or guarantee that concurrent commands choose different
GPUs. Interrupting a GPU wait creates no task. Historical queue state is unused and
untouched. Requested and effective devices appear separately under `gpu_selection`;
see the [execution contract](contracts/execution.md) for telemetry failure, replay and
native owner rules.
