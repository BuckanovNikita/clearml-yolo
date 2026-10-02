# Acceptance quickstart

Use the project running-end-to-end-tests skill and the installation's environment instructions
for credentials, capacity and cleanup. Pass an isolated ClearML project and tags explicitly.
Provide a small immutable ground_truth.csv containing train/val/test with disjoint images and
negative images, and a local detection checkpoint. Select a task-owned `CY_HOME`; automatic
project data, run and owned temporary paths follow the
[filesystem ownership contract](../../docs/filesystem-policy.md). Caller input variables:
`CY_HOME`, `TRUTH`, `MODEL`, `PROJECT`, `TAG`. `CACHE` and `RUNS` below make the automatic
locations visible for inspection.

```bash
export CACHE="$CY_HOME/.cache/clearml-yolo/datasets"
export RUNS="$CY_HOME/runs"
uv sync --locked --dev
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
uv run cy-init-config "$RUNS/config"
uv run cy-train ground_truth="$TRUTH" dataset_cache_dir="$CACHE" ultralytics.model="$MODEL" ultralytics.epochs=2 ultralytics.imgsz=64 ultralytics.batch=2 ultralytics.device=cpu ultralytics.compile=false ultralytics.workers=0 clearml.project_name="$PROJECT" clearml.tags="[$TAG]"
```

Repeat with a fresh task name and the same CSV/cache; inspect one cache entry and unchanged
prepared files. Repeat on the available GPU with explicit device. Run two simultaneous
preparations of the same CSV and interrupt one builder: only complete entries are consumed.
Check original NDJSON filename casing and reject a same-split repeated label stem.
For native YAML training, also verify that real image/label copies and native cache files remain
under `CY_HOME/.cache/clearml-yolo/native-datasets` while every source byte stays unchanged.

```bash
uv run cy ground_truth="$TRUTH" dataset_cache_dir="$CACHE" run_dir="$RUNS/candidate" ultralytics.model="$MODEL" ultralytics.epochs=2 ultralytics.imgsz=64 ultralytics.batch=2 ultralytics.device=cpu ultralytics.compile=false ultralytics.workers=0 clearml.project_name="$PROJECT" clearml.tags="[$TAG]"
```

Inspect ClearML Scalars, Plots, Debug Samples, Configuration and Output Models. Download native
best.pt, load it with YOLO, and compare labels/design/input metadata with trainer/checkpoint.
Download all inventory artifacts and inspect CSV/XLSX contents. There must be no checkpoint
artifact, configuration artifact, raw-metrics dump or diagnostic receipt. Verify one task.
For each `metrics_evaluation_<split>.xlsx`, verify that the only sheets are `summary`,
`per_class` and `confusion_matrix`, and inspect the four CSV sidecars named
`_ground_truth_matches`, `_prediction_matches`, `_thresholds` and `_methodology`.
Verify `metrics_best_confidences_val.csv` remains the canonical exact-threshold table even when
content deduplication satisfies an identical sidecar through alias reuse. A completed
`compare_workbook_<split>.xlsx` must
contain only `Сравнение`, with `_excluded.csv` and `_methodology.csv` sidecars. If automatic
baseline lookup is skipped, the candidate workbook must contain only `Classes` and `Summary`,
with `_thresholds.csv` and `_methodology.csv` sidecars. Confirm JSON manifests/payloads/configs
and PNG diagnostics retain their existing formats.

Use a completed test-owned baseline tagged prod and run another candidate; compare source
links, frozen exact validation thresholds, paired image membership and reports. Exercise
cy-val, cy-compare and cy-report separately with the generated examples. Also compare a
historical artifact-based task and explicit local models with exact thresholds.

Inject rejected artifact/model upload, missing callback registration, flush failure and
interruption in isolated invocations; none may complete successfully. Record dated portable
evidence in docs/evidence; machine-specific task IDs/logs belong with environment instructions.
