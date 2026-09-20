---
name: running-end-to-end-tests
description: >
  Use when verifying clearml-yolo beyond mocked tests: a real cy pipeline run,
  native device execution, ClearML tracking or artifacts, cy-val, or a current-data
  baseline/candidate comparison. Trigger on end to end, full test, real run, smoke test,
  verify against ClearML, coco8, cy run, baseline, compare stage, run tag, or GPU.
---

# Verify clearml-yolo end to end

Use this skill when the change needs real evidence. Unit tests validate contracts without
proving native training, a GPU, the shared ClearML stand, or artifact uploads. Do not run a
live pipeline merely for documentation work.

Read [pipeline prerequisites](references/pipeline-prerequisites.md) before choosing a run.

## Start with static checks

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

`lint-imports` enforces the package boundaries. Use `uv run pre-commit run --all-files` when
the change needs the complete repository hook set.

## Every real run is tagged

A real run acts as `clearml-yolo` on the shared ClearML stand, under one tag and in one
directory outside the checkout. Do not substitute the user's host ClearML. Before minting a
tag from a non-Codex environment, export `INFRA_HARNESS=codex`.

```bash
source scripts/agent_env.sh <slug>
```

The helper preflights capacity, exports stand credentials, mints `CY_RUN_TAG`, creates
`CY_RUN_DIR`, and invokes `scripts/check_env.sh`. It refuses if capacity says WAIT or the
Secret cannot be read; it does not fall back to host credentials.

Every `cy` command must set `run_dir=$CY_RUN_DIR`, the tagged project, the tag list, and
explicit native devices. The output directory isolates files from the checkout; explicit
native mappings leave device selection with Ultralytics:

```bash
uv run cy run_dir=$CY_RUN_DIR \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] \
  +train.ultralytics.device=0 \
  +predict.ultralytics.device=0 ...
```

## Pipeline smoke run

Use a small, valid dataset. ClearML tracking remains enabled. The command below runs in a
tagged project and uses native execution settings:

```bash
uv run cy run_dir=$CY_RUN_DIR/smoke \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] \
  ground_truth=ground_truth.csv \
  +train.ultralytics.data=coco8.yaml \
  +train.ultralytics.epochs=1 \
  +train.ultralytics.device=0 \
  +predict.ultralytics.device=0
```

Verify the task owns one complete lifecycle, and that required checkpoints, prediction and
truth tables, exact thresholds, metrics, plots, reports, effective native arguments, and
manifest are downloadable. Inspect outputs beneath the selected `run_dir`; do not route
pipeline stages through their own output settings.

## Validation and comparison evidence

Run `cy-val` against a checkpoint with validation and test data. Confirm candidate thresholds
are calibrated on validation and reused unchanged for test. The artifact
`metrics_best_confidences_<split>` contains the exact threshold mapping; dashboard values are
rounded.

For a paired comparison, first complete a prod-tagged baseline, then run a candidate in the
same tagged project. The candidate must select that baseline explicitly or through the latest
completed prod-task lookup. Confirm both checkpoints infer the same current test images under
matching settings, and that paired outputs in `comparison_dir` feed the statistical,
developer, and business reports. A first run with no automatic baseline may complete with the
comparison marked skipped. An invalid explicit baseline must fail.

Do not use historical dashboards as comparison input. Do not claim real distributed execution
without specific evidence; CPU and one explicit host GPU are the required real-run gates.

## Clean up on success and failure

```bash
scripts/agent_cleanup.sh
```

It performs tag-scoped ClearML cleanup, proves the result with `ls --prefix "$CY_RUN_TAG"`,
and removes `$CY_RUN_DIR` only when that directory is named after the tag. Use `--dry-run` to
inspect cleanup. Report any intentionally retained object by its full project and task id.
