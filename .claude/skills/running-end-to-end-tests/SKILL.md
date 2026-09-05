---
name: running-end-to-end-tests
description: >
  Use when verifying clearml-yolo beyond mocked tests: a real cy pipeline run,
  GPU queue behavior, ClearML tracking or artifacts, or a baseline comparison.
  Trigger on end to end, full test, real run, smoke test, coco8, cy run,
  baseline, compare stage, or GPU queue.
---

# Verify clearml-yolo end to end

Use this skill when the change needs real evidence. The unit suite can validate
logic without a ClearML server or GPU, but cannot prove pipeline wiring, device
allocation, or artifact upload.

Read [pipeline prerequisites](references/pipeline-prerequisites.md) before
choosing a run. Do not run a live pipeline merely for a documentation change.

## Start with relevant static checks

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

`lint-imports` enforces the project's layer boundaries. `uv run pre-commit run
--all-files` is available when the task needs the repository hook set.

## Offline pipeline smoke run

Use an existing small dataset configuration and a disposable output directory.
This representative command keeps ClearML off and disables comparison, whose
default baseline is resolved through ClearML:

```bash
uv run cy \
  clearml.enabled=false \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  train.ultralytics.name=verify-1ep \
  report/baseline=none \
  skip_compare=true \
  auto_gpu.queue.wait_timeout_seconds=120 \
  run_dir=<disposable-run-directory>
```

The dataset and ground-truth requirements still apply. Check that the selected
run directory contains the checkpoint, predictions, and metrics outputs that
its enabled stages should produce. `run_dir` controls pipeline output routing.

## ClearML-backed run and comparison

First load `running-clearml-server` and pass its authenticated check. Use a
throwaway `clearml.project_name`; do not create verification tasks in a real
project just to obtain a baseline. A first run can legitimately have no prior
baseline. To exercise comparison, complete a baseline run and then a candidate
in the same disposable project, with the baseline selection configured for the
first task.

Verify task completion, one output model when training is enabled, and the
metrics dashboard and exact-confidence artifacts. Exact per-class thresholds
come from `metrics_best_confidences_<split>`, not a rounded dashboard.

## Queue evidence is conditional

Queue behavior needs task-owned concurrent real runs, an available GPU, and a
real terminal for `cy-queue`. Leave queueing enabled for that test, keep each
run's output directory distinct, and inspect only its own entries and leases.
Never cancel, reclaim, pin, or force a queue item owned by another user or
service. `auto_gpu.force=true` bypasses queue and lease safeguards and is not a
queue test.
