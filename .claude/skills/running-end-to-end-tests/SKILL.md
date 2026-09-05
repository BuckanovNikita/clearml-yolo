---
name: running-end-to-end-tests
description: >
  Use when verifying clearml-yolo beyond mocked tests: a real cy pipeline run,
  GPU queue behavior, ClearML tracking or artifacts, or a baseline comparison.
  Trigger on end to end, full test, real run, smoke test, verify against
  ClearML, coco8, cy run, baseline, compare stage, run tag, or GPU queue.
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

## Every real run is a tagged run

A real run acts as the project `clearml-yolo` on the shared ClearML stand
(`running-clearml-server`), under one run tag, in a directory of its own
outside the checkout. Start every session of real runs with

```bash
source scripts/agent_env.sh <slug>
```

It preflights the cluster, exports the stand's credentials, mints `CY_RUN_TAG`
and creates `CY_RUN_DIR`, then runs `scripts/check_env.sh`. It refuses when
the cluster says WAIT or the Secret cannot be read; there is no fallback to the
user's ClearML or to a directory inside the checkout. The offline run below
sources it too: the tag and the directory come from nowhere else.

Every `cy` command line then carries four keys. `run_dir=$CY_RUN_DIR` keeps the
outputs out of the checkout and leaves the user's `runs/latest` alone;
`clearml.project_name="$CY_RUN_TAG clearml-yolo"` and
`clearml.tags=[$CY_RUN_TAG]` put the experiments where the tag's cleanup finds
them; `auto_gpu.queue.wait_timeout_seconds=<n>` gives the queued wait a
deadline so an unattended run fails instead of blocking. Without the last key a
queued run waits for ever: `auto_gpu.wait_timeout_seconds` is read only with
the queue disabled and never bounded the queued wait.

Two different things are called "the queue" here: the local filesystem queue
(`auto_gpu.queue.*`, `cy-queue`) hands out leases on this host's GPU and is
what a `cy` run waits in, while the ClearML queue on the stand (`CLEARML_QUEUE`,
named `agents`) runs tasks in CPU-only pods and is never enqueued to by this
project.

## Offline pipeline smoke run

Use an existing small dataset configuration. This representative command keeps
ClearML off and disables comparison, whose default baseline is resolved through
ClearML:

```bash
uv run cy \
  clearml.enabled=false \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  train.ultralytics.name=verify-1ep \
  report/baseline=none \
  skip_compare=true \
  auto_gpu.queue.wait_timeout_seconds=120 \
  auto_gpu.max_gpus=1 \
  run_dir=$CY_RUN_DIR
```

The dataset and ground-truth requirements still apply. Check that `$CY_RUN_DIR`
contains the checkpoint, predictions, and metrics outputs that its enabled
stages should produce. `run_dir` controls pipeline output routing.

## ClearML-backed run and comparison

First pass `running-clearml-server`'s authenticated check (`check_env.sh` from
`agent_env.sh` is that check). The run's project is `"$CY_RUN_TAG clearml-yolo"`
and nothing else: never create verification tasks in the user's projects or
in another tag's. A first run can legitimately have no prior baseline. To
exercise comparison, complete a baseline run and then a candidate in the same
tagged project, with the baseline selection configured for the first task:

```bash
uv run cy \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] \
  clearml.task_name=baseline \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  report/baseline=none \
  skip_compare=true \
  auto_gpu.queue.wait_timeout_seconds=1800 \
  auto_gpu.max_gpus=1 \
  run_dir=$CY_RUN_DIR/baseline

uv run cy \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] \
  clearml.task_name=candidate \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  report.baseline.project_name="$CY_RUN_TAG clearml-yolo" \
  report.baseline.task_name=baseline \
  report.baseline.tags=[] \
  auto_gpu.queue.wait_timeout_seconds=1800 \
  auto_gpu.max_gpus=1 \
  run_dir=$CY_RUN_DIR/candidate
```

`report.baseline.tags=[]` is needed because the baseline lookup filters on the
`prod` tag by default, and a verification baseline is never promoted.

Verify against the stand's UI at `http://clearml.k8s.localhost/`, in the
project `<run-tag> clearml-yolo`: task completion, one output model when
training is enabled, and the metrics dashboard and exact-confidence artifacts.
Exact per-class thresholds come from `metrics_best_confidences_<split>`, not a
rounded dashboard. `python3 "$CY_INFRA_SKILL_DIR/scripts/clearml.py" --project
clearml-yolo ls --prefix "$CY_RUN_TAG"` lists the same objects from the shell.

## Queue evidence is conditional

Queue behavior needs task-owned concurrent real runs, an available GPU, and a
real terminal for `cy-queue`. Leave queueing enabled for that test, keep each
run's `run_dir` distinct under `$CY_RUN_DIR`, and inspect only its own entries
and leases. The GPU cap for agents is one training at a time (`gpu_runs` in
the k8s-infra registry), so a second concurrent run exists only to be seen
waiting, with a deadline. Never cancel, reclaim, pin, or force a queue item
owned by another user or service. `auto_gpu.force=true` bypasses queue and
lease safeguards and is not a queue test.

## Clean up, on success and on failure

```bash
scripts/agent_cleanup.sh
```

It runs `clearml.py --project clearml-yolo cleanup --prefix "$CY_RUN_TAG"`,
proves the stand is clean with `ls --prefix "$CY_RUN_TAG"`, and removes
`$CY_RUN_DIR`. Add `--dry-run` to see what it would do. Anything that must
survive for the user to look at is named in the final message by its full
project name and task id, or minted under a `-keep` tag in the first place.
