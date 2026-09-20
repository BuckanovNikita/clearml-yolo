# Pipeline prerequisites and observations

## Inputs and configuration

`cy` composes the packaged wrapper configuration. Native Ultralytics YAML is supplied with
`train.cfg=<path>` or `predict.cfg=<path>`; standalone commands use `cfg=<path>`. Native
values are sparse mappings, so preserve the precedence native defaults, cfg YAML, embedded
mapping, then CLI. Add absent native keys with `+ultralytics.key=value` (or the matching
pipeline prefix).

Build the ground-truth CSV before stages that consume it:

```bash
uv run cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

ClearML is required. Do not use `clearml.enabled=false`. `run_dir` routes all pipeline output;
stage-specific paths and conflicting native training `project` or `name` are rejected. A
standalone output-producing command uses a fresh output directory and requires explicit inputs.

With `CY_RUN_TAG` or `INFRA_RUN_TAG`, set the project to `<run-tag> clearml-yolo` and append
the same tag. The examples spell both values out to make cleanup ownership visible.

## Native execution

Set the desired device directly through Ultralytics, for example
`+train.ultralytics.device=0` and `+predict.ultralytics.device=0`. Native `batch`, `amp`, and
`compile` values are forwarded unchanged and recorded as effective arguments. There is no
project queue, GPU lease, batch tuning, or force option.

## What a real run demonstrates

A ClearML-backed run demonstrates the one-task owner, synchronous required artifact uploads,
and actual output paths. Model labels come from the checkpoint, not ClearML metadata. Confirm
that a computation, upload, or interruption failure makes the task and process fail while local
outputs remain available.

Candidate thresholds are calibrated once on validation and frozen for current test evaluation.
Comparison needs a completed baseline with valid exact thresholds, current ground truth, and
both models' inference on the same current test images. The automatic lookup excludes the
current task and only skips if it finds no baseline; invalid explicit selections fail. Reports
use the resulting `comparison_dir`, not historical dashboard artifacts.
