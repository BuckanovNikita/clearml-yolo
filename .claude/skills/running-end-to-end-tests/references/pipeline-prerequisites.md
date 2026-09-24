# Pipeline prerequisites

Use Python and dependencies from `pyproject.toml` and `uv.lock`. Configure ClearML through
its supported SDK environment variables or user configuration before real execution.
Infrastructure access, resource capacity and cleanup are supplied by the environment,
not this repository.

Build the ground-truth CSV before stages that consume it:

```bash
uv run cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

`cy` composes the packaged wrapper configuration. Supply unchanged native YAML with
`train.cfg=<path>` or `predict.cfg=<path>`; standalone commands use `cfg=<path>`.
The precedence is native defaults, YAML, explicit embedded mapping, then CLI overrides.
Add absent keys with `+ultralytics.key=value` or the matching pipeline prefix.

ClearML is required. Pass `clearml.project_name` and `clearml.tags` explicitly when
isolating runs. `run_dir` routes pipeline output; conflicting stage paths or native
training `project`/`name` values fail. Standalone stages require explicit inputs.

Select native `device`, `batch`, `amp` and `compile` settings for the environment.
The application performs no scheduling, GPU leasing, or batch tuning.

Full comparison requires validation/test data and exact baseline thresholds. Candidate
thresholds come from validation only. Both checkpoints must use the same current test
image membership and inference settings; reports consume the resulting `comparison_dir`.
