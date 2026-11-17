# Commands and configuration

CY is operated through Hydra commands: `cy` runs the whole experiment pipeline, and
`cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth` and `cy-export` run single stages. Every one of these commands composes
its settings from packaged defaults, an optional editable YAML tree and command-line
overrides, validates them before any work starts, runs under exactly one ClearML task and
writes its outputs to a predictable directory inside the workspace. `cy-init-config`
exports an editable configuration tree for one selected command. The same configuration
is recorded on the task so that a ClearML Agent can replay the run.

## Behavior

### Command set

| Command | Hydra config | Purpose |
| --- | --- | --- |
| `cy` | `pipeline` | Training, prediction, metrics, comparison, report, visualization |
| `cy-train` | `train` | Training from CSV ground truth |
| `cy-predict` | `predict` | Prediction CSV for selected splits |
| `cy-val` | `val` | Prediction plus metrics |
| `cy-metrics` | `metrics` | Metrics for an existing prediction CSV |
| `cy-compare` | `compare` | Paired comparison of two models on current data |
| `cy-report` | `report` | Developer and business reports from a comparison directory |
| `cy-ground-truth` | `ground_truth` | YOLO `data.yaml` to ground-truth CSV |
| `cy-export` | `export` | Faster R-CNN deployment export and verification |
| `cy-init-config` | — | Editable configuration export; no task |

The utilities `cy-dedup`, `cy-download-weights` and `cy-batch-estimate` use plain
argument parsing, create no ClearML task and are described in
[cache-deduplication](cache-deduplication.md), [model-assets](model-assets.md) and
[batch-estimation](batch-estimation.md). `cy-queue` belongs to the separate queue
package ([queue](queue.md)).

### Composition and overrides

Hydra composes the command's packaged defaults, then a directory given with
`--config-dir` (its files take precedence over packaged ones), then ordinary overrides
such as `ultralytics.epochs=10`. `hydra.job.chdir` is false: the working directory does
not change. Hydra logs go to `CY_HOME/outputs/<date>/<time>-<host>-<pid>` and sweeps to
`CY_HOME/multirun/...`. Before the first job starts, every job's Hydra output, log and
configuration-snapshot destination and every project output route is checked for
containment ([filesystem](filesystem.md)). `--help`, `--hydra-help` and `--info` skip
this preflight; `--help` and `--cfg job --resolve` run no workflow and create no task,
but startup still creates invocation scratch and console logs.

The default `model=ultralytics` exposes two native groups with bare upstream keys:
`ultralytics` (training) and `ultralytics_predict` (prediction). Project training
defaults are `model=yolo11n.pt`, `imgsz=960`, `compile=true`, `nms=true`. Prediction
inherits applicable training values through visible `${ultralytics.<key>}` references and
sets its own `conf=0.001`, `batch=1`, `rect=true`, `save=false`, `verbose=false`,
`device=[-1]`, with `model`, `project` and `name` null. Explicit prediction values,
including nulls, win over inherited ones. Native normalization is recorded separately
from the requested values. Other detector families use `model=<backend>/<preset>` with
typed `model.train` and `model.predict` groups ([detector-families](detector-families.md)).

### Pipeline composition

`cy` runs the stages in this order: training, prediction, metrics (validation calibration
and evaluation), comparison against a baseline on `test`, report, then optional FiftyOne
visualization. Each `skip_<stage>=true` disables one stage. Training uses CSV ground
truth and requires `train` and `val`; enabled prediction or metrics also require the
requested `splits` (default `[train, val, test]`), and an enabled comparison requires
`test`. Prediction always covers `val` plus the requested splits. With training, the
checkpoint that training produces owns inference; with `skip_train=true`, `weights`
names it (default `detect/train/weights/best.pt` in the run directory). With
`skip_train=true skip_metrics=true` and comparison enabled, frozen thresholds are read
from `metrics/frozen_thresholds.json` in the run directory. A report runs after a
successful comparison; with `skip_train=true skip_compare=true` it runs over the
`comparison/` directory already in the run directory, and with training enabled and
`skip_compare=true` it is skipped. Stage outcomes are written to
`pipeline_outcome.json` and `pipeline_outcome.txt`; the outcome policy is in
[clearml-publication](clearml-publication.md).

### Output routing and run identity

Every experiment command owns one ClearML task. The pipeline task is named
`clearml.task_name`; a standalone stage task is named `<task_name>/<stage>`. Implicit
outputs use `CY_HOME/runs/<project>/<task>-<task-id>/`, where each component is
percent-encoded as one portable path component (`.` and `~` are encoded, and names such
as `latest`, `CON` or `COM1` are altered). Standalone `output_dir` defaults to
`<run root>/<stage>` and `output` to `<run root>/<stage>.csv`; standalone training writes
to `<run root>/detect` unless `ultralytics.project` is set.

For `cy`, `run_dir` wins, otherwise `run_id` selects `CY_HOME/runs/<run_id>`, otherwise
the task-derived root is used. An existing `run_dir` or `run_id` directory is reused as
is and never cleared, so files of an earlier run stay beside the new ones; use a new
directory for each experiment. The run directory holds `detect/train`, `native/predict`,
`predictions.csv`, `metrics/`, `comparison/` and `reports/`. Native `project`/`name`
values must equal the routed ones, and `save_dir` is rejected. `runs/latest` is a symlink
to the newest pipeline run directory or task-derived standalone training root inside the
workspace (standalone training with an explicit `ultralytics.project` leaves it
unchanged); a run outside the workspace leaves it unchanged, a non-symlink at that name
is moved to `latest-displaced-<host>-<pid>`, and a failure to update it only logs a
warning.

### Multirun tags

Every effective MULTIRUN (`-m` or saved `hydra.mode=MULTIRUN`, including a one-job sweep)
receives one fresh ClearML tag `multirun-YYYYMMDD-HHMMSS-<six-word-phrase>` (UTC), shared
by all its jobs and appended to explicit `clearml.tags`. An ordinary RUN adds no tag.
Sweeps run sequentially with Hydra's BasicSweeper and BasicLauncher.

### Selected configuration export

`cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]` writes, without a
task or model runtime, one `<command>.yaml` wrapper (default `cy`), its local command base
(`pipeline.yaml`, `train.yaml`, ...) and the YAML groups that the selection needs.
Commands that run a model write `model/<selection>.yaml` (`model/ultralytics.yaml` by
default, `model/<backend>/<preset>.yaml` for `--model backend/preset`). The five
prediction commands (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`) also write
empty `ultralytics/_defaults.yaml` and `ultralytics_predict/_defaults.yaml`, and for YOLO
`ultralytics/default.yaml` and `ultralytics_predict/default.yaml` with upstream comments
and stage-irrelevant keys commented out. `cy` and `cy-train` also write both
augmentation profiles and their model overlays. `cy-export` defaults to
`fasterrcnn/resnet50_fpn`. `cy-metrics`, `cy-report` and
`cy-ground-truth` write no model files. Unrelated files in the directory are never
changed. For a non-YOLO preset, edit the model file's `train` and `predict` sections
without changing `backend` and `preset`; set the CSV and ClearML identity in the wrapper.
Run a tree with `<command> --config-dir DIR --config-name <command>`, for example
`cy-metrics --config-dir DIR --config-name cy-metrics`. Packaged public defaults stay on
the search path after the local directory, so a generated tree that lacks a group file
still composes from the packaged defaults. Python callers use
`dump_config_tree(directory, *, command="cy", model=None, overwrite=False)`.

### Startup configuration

After composition and any Agent replay, the task receives JSON Configuration Objects:
`run`, the resolved executable inputs (YOLO keeps its native groups and only the model
backend/preset; other detectors keep `model` and omit the YOLO groups, with
`dataset_format=coco`), and `run_overrides`, an informational recursive difference from
the built-in defaults of the same command and preset that keeps meaningful `false`, zero,
null and empty values and excludes routing, tracking destinations and result
provenance. Replay and cloning use `run`, never `run_overrides`. Training publishes
sanitized `General` parameters before dataset preparation; commands that skip training
publish none. Attached YAML/JSON configuration files (the `cy-ground-truth` `data.yaml`,
a report configuration) are resolved against the command's configuration, with file
values taking precedence as whole top-level values, and only the file's own fields are
published, sanitized, as a Configuration Object.

### ClearML Agent replay

When an experiment command's recorded entrypoint runs under an externally managed
ClearML Agent, CY reads one detached snapshot of the remote task before mandatory-input
validation and backend selection, applies its canonical `run` object to the launch
configuration, initializes the matching runtime and joins the same task. An absent `run`
object permits complete explicit launch arguments. YOLO training applies remote
scientific `General` overrides over `run.ultralytics`, except a recorded batch when the
request is `batch=null`; a YOLO task whose `run` lacks the `ultralytics` group restores it
from `General`, while a present group, even an empty one, wins. Other families replay
`run.model`, which `General` never overrides. Explicit routes recorded in `run`
(`run_dir`, `run_id`, `output_dir`, `output`) are replayed and must resolve inside the
Agent's `CY_HOME`; native `project`, `name` and `save_dir` come only from the current
request, and implicit routes derive from the joined task. Agent `CUDA_VISIBLE_DEVICES`
and native device settings are used unchanged; no queue package, configuration or
reservation is involved, and CY installs no dependencies at execution time.

### Git workspace warning

Each experiment command checks its launch directory once, inside console capture and
before Hydra composition, including `--help` and multiruns. Unless
`git rev-parse --is-inside-work-tree`, run without inherited `GIT_*` variables, succeeds
with `true` (repository roots, subdirectories, unborn repositories, linked worktrees and
submodules; a bare repository does not qualify), one warning goes
to stderr and the captured logs: `Git working tree could not be verified for launch
directory '<dir>': <reason>. ... Continuing.` The check never changes Git state, stdout
or the exit status, and is independent of `CY_HOME`. `cy-init-config`, the utilities
and direct Python workflow calls do not perform it.

## Configuration

| Setting | Default | Notes |
| --- | --- | --- |
| `--config-dir`, `--config-name` | packaged | Local tree from `cy-init-config` |
| `clearml.project_name`, `task_name`, `tags` | `clearml-yolo`, `yolo-run`, `[]` | Task identity and output root |
| `clearml.output_uri` | `true` | `null`, `false` and `""` are rejected |
| `run_dir`, `run_id` | `null` | Pipeline routing |
| `output_dir`, `output` | `null` | Standalone routing |
| `skip_train` ... `skip_compare` | `false` | Pipeline stages |
| `splits` | `[train, val, test]` | Pipeline, `cy-val`, `cy-metrics` |
| `ultralytics.*`, `ultralytics_predict.*` | upstream plus project values | YOLO only |
| `model` | `ultralytics` | `model=<backend>/<preset>` |

Required inputs left as `???` must be supplied: `ground_truth` for `cy`, `cy-train`,
`cy-predict`, `cy-val`, `cy-metrics` and `cy-compare`; `predictions` for `cy-metrics`;
`comparison_dir` for `cy-report`; `data_yaml` for `cy-ground-truth`.

### Rejected legacy controls

`queue.*`, `autogpu.*`, `auto_gpu.*` and `hydra/launcher=cy_queue` are rejected in CLI
overrides, saved YAML (including its defaults lists) and replayed configurations with:
`Legacy queue/autogpu controls are removed from direct cy commands. Remove these settings
from CLI overrides and saved YAML. Use cy-queue submit for scheduled execution; direct
commands preserve native devices.` `clearml.enabled` does not exist and fails
composition. Saved trees whose `_target_` strings name modules outside the current
package fail at instantiation; regenerate them with `cy-init-config` after backing up
custom values.

## Failure behavior

- Unknown top-level keys fail with `Unsupported wrapper settings: [...]`; unknown native
  keys, non-null `cfg` or `embed`, `task` other than `detect`, a wrong `mode` and invalid
  `imgsz` fail validation before work. Known keys that belong to the other stage are
  excluded from execution, not rejected.
- Changed settings in the inactive family's groups fail in both directions
  (`Changed ultralytics settings [...] are inactive for <backend>/<preset>; use
  model.train instead`).
- Sweep syntax without MULTIRUN fails with `Use -m or hydra.mode=MULTIRUN to expand a
  Hydra sweep`; another sweeper or launcher fails with `cy supports sequential
  BasicSweeper/BasicLauncher sweeps; use cy-queue for concurrent execution`.
- Pipeline stage groups accept only their own keys (`Pipeline <stage> keys [...] are
  unsupported; outputs use run_dir`); `weights` without `skip_train=true`, a
  `dataset_cache_dir` inside the run directory and conflicting native routes fail.
- `cy-init-config` fails before writing anything when a selected file exists without
  `--force`, when a selected destination is a symlink, directory or other non-regular
  file (also with `--force`), when a parent is a symlink, for an unknown command, for a
  model with a command that runs none, for a non-Faster R-CNN `cy-export` model, and
  for a `DIRECTORY` outside `CY_HOME` (the containment message in
  [filesystem](filesystem.md)).
- A present but empty or malformed canonical `run` object on an Agent fails with
  `Effective ClearML run configuration must not be empty` or a type error instead of
  using local defaults; replay cannot switch an initialized runtime between YOLO and
  another detector family (`Relaunch with model=...`).
- An attached configuration file whose values cannot be resolved (unknown references or
  resolvers, cycles, missing mandatory or environment values, computed targets such as
  `${${key}}`) fails with `Configuration values could not be resolved: ...`, naming at
  most the field, never its value.
- Git warning causes (missing Git, timeout after five seconds, OS errors, other output)
  never fail the command.

## Limits

- Only sequential Hydra sweeps run directly; concurrent execution uses `cy-queue`.
- Composition does not prove that inputs exist, checkpoints load, GPUs have capacity or
  publication succeeds.
- `run_overrides` is informational and does not drive replay or cache identity.
- An unversioned launch directory is reported, never initialized; `git init` is the
  user's choice.

## Code and tests

- [hydra/common.py](../../src/clearml_yolo/entrypoints/hydra/common.py) — launch, Agent
  replay, `run` publication, implicit routes
- [hydra/configs.py](../../src/clearml_yolo/entrypoints/hydra/configs.py) and
  [declarations.py](../../src/clearml_yolo/entrypoints/hydra/declarations.py) — commands
- [hydra/validation.py](../../src/clearml_yolo/entrypoints/hydra/validation.py) and
  [sweeps.py](../../src/clearml_yolo/entrypoints/hydra/sweeps.py) — preflight, multirun
- [hydra/config_tree.py](../../src/clearml_yolo/entrypoints/hydra/config_tree.py) —
  `cy-init-config`;
  [config_resolution.py](../../src/clearml_yolo/entrypoints/hydra/config_resolution.py) —
  attached configuration files
- [use_cases/pipeline.py](../../src/clearml_yolo/application/use_cases/pipeline.py),
  [run_identity.py](../../src/clearml_yolo/adapters/storage/run_identity.py),
  [git_workspace.py](../../src/clearml_yolo/adapters/runtime/git_workspace.py)
- Tests: [test_configs](../../tests/test_configs.py),
  [test_config_tree](../../tests/test_config_tree.py),
  [test_config_self_containment](../../tests/test_config_self_containment.py),
  [test_multirun_tags](../../tests/test_multirun_tags.py),
  [test_hydra_sweep_configuration](../../tests/test_hydra_sweep_configuration.py),
  [test_agent_replay](../../tests/test_agent_replay.py),
  [test_git_workspace](../../tests/test_git_workspace.py),
  [test_run_identity](../../tests/test_run_identity.py),
  [test_pipeline](../../tests/test_pipeline.py),
  [test_configuration_publication](../../tests/test_configuration_publication.py),
  [test_config_resolution](../../tests/test_config_resolution.py)
- Agent replay is verified only for `train` and `pipeline` against a simulated remote
  task; no automated test runs under a real ClearML Agent.
