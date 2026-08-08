---
name: running-end-to-end-tests
description: |
  Use when verifying clearml-yolo beyond the mocked unit suite: running the whole `cy` pipeline for real,
  checking a change end to end against the local ClearML server, producing a baseline to compare against,
  or deciding what "the full tests" means for this project. Also use before declaring a pipeline, GPU,
  ClearML-tracking or report/compare change done.
  Trigger on: "end to end", "full test", "real run", "smoke test", "run the pipeline", "verify against ClearML",
  "coco8", "cy run", "baseline run", "compare stage".
---

# Running clearml-yolo end to end

`uv run pytest` is **fully mocked** — no server, no GPU, no ultralytics. It cannot catch a broken
pipeline wiring, a stage that mis-handles a device, or a ClearML artifact that never uploads. Those need a
real `cy` run. Both layers are part of "the full tests"; neither substitutes for the other.

## 1. Static checks first — all four

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

`lint-imports` is not optional and is the one most often forgotten: it enforces the layering contracts in
`pyproject.toml` (`apps` → `config_tree` → `configs` → `tasks` → `comparison` → domain), including that
`clearml` stays behind the `clearml_*` adapters. `uv run pre-commit run --all-files` runs exactly these
four through the same locked `dev` group.

## 2. Offline pipeline run — no server needed

Proves train → predict → metrics → report wiring on coco8 in about a minute. Run this first: if it
fails, ClearML is not your problem.

```bash
uv run cy \
  clearml.enabled=false \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  train.ultralytics.name=verify-1ep \
  report/baseline=none \
  skip_compare=true \
  auto_gpu.scale_to_vram=false \
  auto_gpu.wait_timeout_seconds=120
```

Add `train.ultralytics.project=`, `predict.output=`, `metrics.output_dir=`, `report.output_dir=` pointing
into your scratchpad to keep `runs/` clean.

**Expected end state:** `metrics.output_dir` holds `full_dashboard_{train,val,test}.xlsx`,
`matrix_*.xlsx`, `метрики_дтрк_*.xlsx` and four `*_confidence_intervals.png`; the predictions CSV has a
row per detection; the last log lines are `Baseline disabled; publishing new metrics without comparison`
and `Skipping comparison stage`.

**`report.output_dir` is empty, and that is correct.** With `report/baseline=none` there is nothing to
compare against, so the report stage publishes metrics without writing workbooks. Do not read the empty
directory as a failure.

## 3. ClearML-backed run

**REQUIRED SUB-SKILL:** confirm the server is up *and authenticated* first — use `running-clearml-server`.
`./scripts/check_env.sh` is the check that matters; a reachable server with stale `~/clearml.conf`
credentials fails ~30 s into the run with `LoginError ... 401`.

```bash
uv run cy \
  clearml.project_name=cy-verify \
  clearml.task_name=verify-1ep \
  clearml.tags=[prod] \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  auto_gpu.scale_to_vram=false \
  auto_gpu.wait_timeout_seconds=120
```

Use a throwaway `clearml.project_name`. The baseline lookup is **scoped to the run's own project**
(`report.py` falls back to the pipeline's project name), so a `cy-verify` task tagged `prod` can never
become the baseline for real `clearml-yolo` runs. Never point a verification run at the real project just
to get a baseline.

**Verify afterwards** at http://localhost:8580 — the task exists under `cy-verify`, carries the `prod`
tag, registered an output model, and uploaded the `metrics_dashboard_full*` and `best_confidences*`
artifacts. A task that appears but registered no output model means training uploaded nothing, which the
downstream `weights=<task-id>` path depends on.

## 4. Exercising compare

The compare stage needs a *previous* completed task to compare against, so it takes two runs: the first
is the baseline, the second compares. On a fresh project the first run finds no baseline and warns —
that warning is the expected first-run result, not a bug.

```bash
uv run cy clearml.project_name=cy-verify clearml.task_name=baseline clearml.tags=[prod] ...   # run 1
uv run cy clearml.project_name=cy-verify clearml.task_name=candidate ...                      # run 2
```

## Overrides that matter on this box

`auto_gpu.scale_to_vram=false` pins the batch to the 24 GB `reference_vram_gb` instead of scaling it up
to the 5090's 32 GB. The GPU is shared with CVAT and the ClearML server, so verification runs must not
claim the full card. Do **not** raise `reference_vram_gb` to 32 to "match the hardware" — that is a
batch-sizing knob, not a memory cap.

`auto_gpu.wait_timeout_seconds=120` stops a run from blocking for the default hour when another process
holds the card.

## Common mistakes

| Mistake | Reality |
|---|---|
| "`uv run pytest` passed, so the pipeline works" | The suite is fully mocked. It never runs a stage for real. |
| Skipping `lint-imports` | It is the only check that catches a layering violation, and pre-commit will reject the commit. |
| Reading an empty `report.output_dir` as failure | Expected with `report/baseline=none`. |
| First ClearML run warning "no completed task tagged prod" | Expected on a fresh project; compare needs a prior run. |
| Verifying against the real `clearml-yolo` project | Pollutes the `prod` baseline other runs resolve against. Use a throwaway project. |
| Treating `debug.ping` as proof ClearML works | It answers unauthenticated. Use `./scripts/check_env.sh`. |
