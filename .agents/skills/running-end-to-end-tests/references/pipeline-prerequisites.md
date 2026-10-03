# Pipeline prerequisites

Use Python and dependencies from `pyproject.toml` and `uv.lock`. Configure ClearML through
its supported SDK environment variables or user configuration before real execution.
Infrastructure access, resource capacity and cleanup are supplied by the environment,
not this repository.

Set `CY_HOME` to the invocation workspace (default: launch working directory) for project
datasets, task outputs and owned temporary files. General runner/library caches and Python
bytecode retain their normal defaults. Explicit output/cache paths remain valid elsewhere;
physically home-resident project write destinations warn without rejection. Follow the
[filesystem contract](../../../../docs/filesystem-policy.md).
Preserve source images and existing user configuration.

Build the ground-truth CSV before stages that consume it:

```bash
uv run cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

`cy` composes the packaged wrapper configuration. Generate examples with
`cy-init-config configs`, then paste native YAML into `configs/ultralytics/default.yaml`.
Prediction overrides live in `configs/ultralytics_predict/default.yaml`. Invoke generated
examples with `--config-dir configs --config-name cy`; override shared values with
`ultralytics.key=value` and prediction values with `ultralytics_predict.key=value`.
Raw `cfg` loading and nested `train.ultralytics`/`predict.ultralytics` are removed.

ClearML is required for execution commands. Pass `clearml.project_name` and
`clearml.tags` explicitly when isolating runs. `run_dir` routes pipeline output;
conflicting stage paths or native training `project`/`name` values fail. Standalone
stages require explicit inputs. `cy-init-config DIRECTORY [--force]` writes only
editable configuration examples without creating a ClearML task.

Select native `device`, `batch`, `amp` and `compile` settings for the environment. The five model
commands derive whole-GPU demand from native `device` and coordinate through a user-wide, same-OS
strict FIFO queue. There is no separate GPU-count setting. A training integer means one GPU, a list
uses its length, every automatic `-1` contributes one, null/empty/`cuda` means one, and `cpu`/`mps`
means zero. GPU inference requires one device; a pipeline reserves the maximum training/inference
demand before starting. Keep inherited `CUDA_VISIBLE_DEVICES` accurate for the test environment.

Before a native queue test, establish that the request does not exceed the visible whole-GPU set
and that unrelated compute processes do not own candidate devices. Waiting occurs before ClearML
task creation and native GPU context. Multi-GPU acceptance must observe verified training/DDP
cleanup before N-1 reservations are released, then confirm prediction and comparison use retained
child-local device `0` through job exit. Record physical multi-GPU execution as unverified when it
was not exercised. The application does not tune batches and does not coordinate MIG, remote hosts,
or separate operating-system instances.

Full comparison requires validation/test data and exact baseline thresholds. Candidate
thresholds come from validation only. Both checkpoints must use the same current test
image membership and inference settings; reports consume the resulting `comparison_dir`.
