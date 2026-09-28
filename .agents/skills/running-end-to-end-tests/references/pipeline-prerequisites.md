# Pipeline prerequisites

Use Python and dependencies from `pyproject.toml` and `uv.lock`. Configure ClearML through
its supported SDK environment variables or user configuration before real execution.
Infrastructure access, resource capacity and cleanup are supplied by the environment,
not this repository.

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
stages require explicit inputs. `cy-init-config DIRECTORY [--force]` only writes
editable configuration examples and does not create a ClearML task.

Select native `device`, `batch`, `amp` and `compile` settings for the environment.
The application performs no scheduling, GPU leasing, or batch tuning.

Full comparison requires validation/test data and exact baseline thresholds. Candidate
thresholds come from validation only. Both checkpoints must use the same current test
image membership and inference settings; reports consume the resulting `comparison_dir`.
