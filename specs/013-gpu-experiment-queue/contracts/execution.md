# Queued execution and Hydra launcher contract

## Command routing

The queue wraps `cy`, `cy-train`, `cy-predict`, `cy-val`, and `cy-compare` when derived demand is
positive. CPU/MPS-only invocations and `cy-metrics`, `cy-report`, `cy-ground-truth`, and
`cy-init-config` run immediately through their existing boundaries.

Waiting occurs before ClearML task creation and before native GPU runtime initialization. An
admitted job starts a fresh execution child with assigned UUIDs as its visible set. Native training
receives concrete child-local indices; GPU prediction, validation, and comparison receive local
device `0`. Requested configuration remains unchanged in its provenance record; effective
configuration records the translated values.

Training retains `ultralytics_requested.yaml`; prediction retains
`ultralytics_predict[_<index>]_requested.yaml` alongside effective YAML. Comparison preserves its
role/split requested snapshots. Canonical run configuration records requested devices, effective
local devices, reserved UUIDs and phase. A ClearML replay that increases demand beyond the admitted
reservation fails before native execution.

The child owns exactly one ClearML task and the current callback, publication, failure, flush, and
completion lifecycle. Child failure or interruption returns nonzero. The supervisor always attempts
deterministic release using the recorded ownership relationship.

## Demand normalization

| Native intent | Training demand |
|---|---:|
| nonnegative integer such as `2` | 1 |
| list such as `[0,1]` | 2 |
| automatic integer/list entry `-1` | 1 per entry, physical ID ignored |
| null, empty, or `cuda` | 1 |
| `cpu` or `mps` | 0 |

GPU-backed prediction, validation, and comparison demand one. Pipeline initial demand is the
maximum of training demand and the one-GPU downstream inference demand. No separate count setting
exists.

## Hydra launcher

`src/hydra_plugins/cy_queue/launcher.py` is the default local launcher for the five model commands
and supports BasicSweeper. Its plugin package is included in the distribution beside
`clearml_yolo`.

- Submit composed jobs to the queue in Hydra order.
- Admit and run several fresh child jobs concurrently only as FIFO and capacity permit.
- Preserve Hydra callbacks, job environment, per-job output directory, and configured chdir.
- Return one `JobReturn` per submitted job in the original order.
- Preserve each job's success or failure and make any failure produce a nonzero command outcome.

Other sweepers, a persistent daemon, priority, bypass, remote launchers, cross-host coordination,
and MIG scheduling are outside this contract.
