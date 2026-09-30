# Acceptance quickstart

Use the project running-end-to-end-tests skill and the installation's environment instructions
for credentials, capacity and cleanup. Pass an isolated ClearML project and tags explicitly.
Provide a small immutable ground_truth.csv containing train/val/test with disjoint images and
negative images, and a local detection checkpoint. Caller input variables:
`TRUTH`, `MODEL`, `CACHE`, `RUNS`, `PROJECT`, `TAG`.

```bash
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

```bash
uv run cy ground_truth="$TRUTH" dataset_cache_dir="$CACHE" run_dir="$RUNS/candidate" ultralytics.model="$MODEL" ultralytics.epochs=2 ultralytics.imgsz=64 ultralytics.batch=2 ultralytics.device=cpu ultralytics.compile=false ultralytics.workers=0 clearml.project_name="$PROJECT" clearml.tags="[$TAG]"
```

Inspect ClearML Scalars, Plots, Debug Samples, Configuration and Output Models. Download native
best.pt, load it with YOLO, and compare labels/design/input metadata with trainer/checkpoint.
Download all inventory artifacts and inspect CSV/XLSX contents. There must be no checkpoint
artifact, configuration artifact, raw-metrics dump or diagnostic receipt. Verify one task.

Use a completed test-owned baseline tagged prod and run another candidate; compare source
links, frozen exact validation thresholds, paired image membership and reports. Exercise
cy-val, cy-compare and cy-report separately with the generated examples. Also compare a
historical artifact-based task and explicit local models with exact thresholds.

Inject rejected artifact/model upload, missing callback registration, flush failure and
interruption in isolated invocations; none may complete successfully. Record dated portable
evidence in docs/evidence; machine-specific task IDs/logs belong with environment instructions.
