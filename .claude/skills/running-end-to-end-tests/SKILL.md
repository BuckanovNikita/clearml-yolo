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

`uv run pytest` needs **no server and no GPU** — `clearml`, `ultralytics` and `torch` are stubbed per
test, in the tests that touch them. (`tests/test_ultralytics_params.py` deliberately imports the real
`ultralytics.cfg`: its job is to check the vendored parameter files against the installed package.) It
cannot catch a broken pipeline wiring, a stage that mis-handles a device, or a ClearML artifact that never
uploads. Those need a real `cy` run. Both layers are part of "the full tests"; neither substitutes for the
other.

## 1. Static checks first — all four

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

`lint-imports` is not optional and is the one most often forgotten: it enforces the layering contracts in
`pyproject.toml` (`apps` → `config_tree` → `configs` → `tasks` → `comparison` → domain →
`run_queue`/`run_identity`), including that `clearml` stays behind the `clearml_*` adapters.
`uv run pre-commit run --all-files` runs these four through the same locked `dev` group, after the upstream `pre-commit-hooks` set (`check-yaml`,
`check-toml`, merge conflicts, file size, whitespace, end-of-file), which lives in pre-commit's own
environment rather than in `dev`.

## 2. Offline pipeline run — no server needed

Proves train → predict → metrics → report wiring on coco8. Run this first: if it fails, ClearML is not
your problem.

```bash
uv run cy \
  clearml.enabled=false \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  train.ultralytics.name=verify-1ep \
  report/baseline=none \
  skip_compare=true \
  auto_gpu.queue.enabled=false \
  auto_gpu.wait_timeout_seconds=120
```

Add `run_dir=<scratchpad>/cy-verify` to keep `runs/` clean. That is now the **only** way to redirect
output: the per-stage keys that used to do it — `predict.output=`, `metrics.output_dir=`,
`report.output_dir=`, `compare.output_dir=` — no longer compose inside `cy` (`Key 'output' not in
'Config'`), because the run hands each stage a path under `run_dir`. `train.ultralytics.project=` still
composes but the run overwrites it, which is worse than a refusal: the override looks accepted and does
nothing.

Two overrides here are load-bearing, not decoration. `skip_compare=true` is required whenever
`clearml.enabled=false`: the comparison resolves its baseline out of ClearML and has no project to
search, which `_check_comparison_baseline` rejects before training starts. And `report/baseline=none` is
a group override that composes only against the packaged config; from a `cy-init-config` folder it is
`report.baseline.source=none`.

The run also refuses to start if `ground_truth` does not point at an existing CSV and any of predict,
metrics or compare will run. It refuses too if a run that trains names `predict.ultralytics.imgsz`
outright and that resolution is not the one `train.ultralytics.imgsz` is training at — leave predict's
null and the checkpoint answers it. And a skipped stage whose consumer still runs is checked the same
way: `skip_predict` without a `predictions.csv`, or `skip_metrics` without a dashboard workbook under
`metrics/`, is refused rather than discovered inside pandas or, worse, as an empty report and exit
code 0. Every one of these refusals happens before training, so a mis-specified run costs seconds rather
than a full training pass.

**Which directory those inputs are looked for in is not always `runs/latest`.** A run told which run it
is — `run_id=` or `run_dir=`, which is exactly what the scratchpad advice above does — reads its **own**
directory, because naming a directory means re-entering it. So `run_dir=<scratchpad>/cy-verify
skip_predict=true` scores the CSV in that scratchpad directory and refuses naming that path when it is
not there; only a run that named neither key falls back to `runs/latest`, resolved before the run
repoints the link. Exercising the skip flags against a *previous* run therefore means leaving both keys
unset, or pointing `run_dir=` at the directory that previous run actually wrote.

**Expected end state:** everything is under one run directory — `runs/<task_name>-<host>-<stamp>-<pid>/`,
with `runs/latest` symlinked to it, or under `run_dir` if you named one. `<run_dir>/metrics` holds
`full_dashboard_{train,val,test}.xlsx`, `matrix_*.xlsx`, `метрики_дтрк_*.xlsx` and four
`*_confidence_intervals.png`; `<run_dir>/predictions.csv` has a row per detection;
`<run_dir>/detect/<name>/weights/best.pt` is the checkpoint. The last log lines are `Baseline disabled;
publishing new metrics without comparison` and `Skipping comparison stage`. Check `runs/latest` resolves
to this run: it is what `skip_train=true` without `weights` reads the checkpoint through, and what a
standalone `cy-predict` with no `weights` resolves against.

A standalone `cy-predict` resolves that checkpoint under its **own** `clearml.task_name` —
`runs/latest/detect/<clearml.task_name>/weights/best.pt` — never under `train.ultralytics.name` and
never under whatever trained last. The command above trains as `verify-1ep` while leaving the experiment
name at its default, so a bare `cy-predict` after it refuses by name (`No checkpoint at …`) before it
opens a ClearML task, and that refusal is the behaviour working: the path used to reach ultralytics as a
failed download of a pretrained model. Chain the two by name (`cy-train clearml.task_name=X` then
`cy-predict clearml.task_name=X`), or name the model outright with
`weights=<run_dir>/detect/verify-1ep/weights/best.pt`.

**`<run_dir>/reports` is empty, and that is correct.** With `report/baseline=none` there is nothing to
compare against, so the report stage publishes metrics without writing workbooks. Do not read the empty
directory as a failure.

## 3. ClearML-backed run

**REQUIRED SUB-SKILL:** confirm the server is up *and authenticated* first — use `running-clearml-server`.
`./scripts/check_env.sh` is the check that matters; a reachable server with stale `~/clearml.conf`
credentials fails partway into the run with `LoginError ... 401`.

```bash
uv run cy \
  clearml.project_name=cy-verify \
  clearml.task_name=verify-1ep \
  clearml.tags=[prod] \
  train.ultralytics.data=coco8.yaml \
  train.ultralytics.epochs=1 \
  auto_gpu.queue.enabled=false \
  auto_gpu.wait_timeout_seconds=120
```

Use a throwaway `clearml.project_name`. The baseline lookup is **scoped to the run's own project**
(`report.py` falls back to the pipeline's project name), so a `cy-verify` task tagged `prod` can never
become the baseline for real `clearml-yolo` runs. Never point a verification run at the real project just
to get a baseline.

**Expected end state:** the task reaches `completed` under `cy-verify` carrying the `prod` tag, registers
one output model, and holds `metrics_dashboard_full_{train,val,test}` and
`metrics_best_confidences_{train,val,test}` among its artifacts. The last lines warn that no `prod`-tagged task was found to
compare against; on a fresh project that is the correct first-run result.

A task that appears but registers **no output model** means training uploaded nothing, which the
downstream `weights=<task-id>` path depends on. Check it in the UI at http://localhost:8580, or read it
back with `Task.get_task(task_id=...).get_models()["output"]`.

## 4. Exercising compare

The compare stage needs a *previous* completed task to compare against, so it takes two runs: the first
is the baseline, the second compares. On a fresh project the first run finds no baseline and warns —
that warning is the expected first-run result, not a bug.

```bash
uv run cy clearml.project_name=cy-verify clearml.task_name=baseline clearml.tags=[prod] ...   # run 1
uv run cy clearml.project_name=cy-verify clearml.task_name=candidate \
  compare.bootstrap_iterations=200 ...                                                        # run 2
```

`compare.bootstrap_iterations=200` keeps a verification run quick; the default 10000 is for real
comparisons, not for proving the wiring.

**Expected end state of run 2:** `<run_dir>/comparison` holds `compare_workbook_<split>.xlsx` plus the
re-inferred `baseline_predictions_*` / `candidate_predictions_*` CSVs, and the log ends with
`Comparison of split '<split>': <n> classes compared, <n> excluded, <n> degraded`. Because the report stage now
resolves a baseline, `<run_dir>/reports` also fills with `report_dev_*`, `report_business_*` and
`baseline_*` workbooks per split — the contrast with run 1's empty report directory is the check that the
baseline actually resolved. Both runs have their **own** run directory: run 2's comparison must not be
sitting in run 1's.

## 5. Two runs at once — the queue and the run directory

The mocked suite covers the queue unusually well (it is pure filesystem, pointed at `tmp_path`), but it
cannot see two processes racing one card, an NVML survey, or a `runs/latest` symlink. That needs two
terminals.

**This box has one GPU**, so the 4+4 split the queue exists for is not verifiable here. The observable
equivalent is two runs each asking for one card: the second must queue behind the first rather than
collide with it or hang. Keep `auto_gpu.queue.enabled` at its default here — switching it off is what
the other sections do, and it is the very thing under test. Do not reach for `auto_gpu.min_gpus=2` to
simulate the split: a request for more cards than the machine has is refused right after the first
survey, before anything is enqueued, naming `auto_gpu.min_gpus`. That refusal is itself worth exercising
once — `entries/` must stay empty afterwards.

Both runs below name `auto_gpu.max_gpus=1`, which also keeps them off the settling pass: a run that names
no ceiling and could take more than `min_gpus` cards enqueues and waits one `queue.poll_seconds` before
claiming, so that a run starting inside that window is in the order and gets its share. On a one-card box
there is never more than `min_gpus` free, so the pass never triggers here either way — which is exactly
why the 8-card behaviour lives in `tests/test_gpu.py` against a fabricated survey.

```bash
# terminal 1
uv run cy clearml.enabled=false train.ultralytics.data=coco8.yaml train.ultralytics.epochs=1 \
  clearml.task_name=par-a report/baseline=none skip_compare=true \
  auto_gpu.max_gpus=1

# terminal 2, started while the first is training
uv run cy clearml.enabled=false train.ultralytics.data=coco8.yaml train.ultralytics.epochs=1 \
  clearml.task_name=par-b report/baseline=none skip_compare=true \
  auto_gpu.max_gpus=1

# terminal 3
uv run cy-queue
```

`cy-queue` needs a real terminal — it draws a live table and reads single keypresses, so it refuses with
exit code 2 when stdin or stdout is a pipe. Watching a queue somewhere else is `cy-queue --dir <path>`;
the default is `/tmp/clearml-yolo/<hostname>`, also settable per-run with `auto_gpu.queue.dir` or
`$CLEARML_YOLO_QUEUE_DIR`.

Checks, in order:

1. **Run B logs its queue position**, naming who is ahead of it, rather than colliding or hanging. On
   this WSL box that line is the whole point: `/dev/dxg` is one device for every card, so before leases
   a peer run marked *all* cards occupied and the second run sat in the wait loop for the full
   `wait_timeout_seconds`. A's pid is now subtracted from that count along with its whole process group.
2. **`cy-queue` shows A holding a card above B waiting.** Both are named `<host>-<pid>` there, not
   `par-a`/`par-b`: the queue identifies the *process* (stable across stages so predict recognises the
   lease train took), while the run directory is named after the experiment. A's elapsed time counts up
   from the moment its lease was claimed, which the lease records for itself; `-` there means a lease
   claimed but not yet written, or one written before the queue recorded starts at all. Pin (`t`),
   cancel (`c`) and reclaim (`r`) each
   take effect within one poll interval. A cancelled run says so and stops — it does not start.
   Pressing `r` on a live holder must refuse: the claim is taken and given straight back, so a running
   training cannot be evicted from the viewer. Pressing `t` on a run that already holds cards must
   refuse too — it is running, not waiting.
3. **B starts after A releases**, and `served/<user>` under the queue directory gains an entry. Start a
   third run C while B is still queued: C must land *behind* B even at the instant A releases its card.
   Entries are read before the survey precisely so a newcomer cannot jump the line, and that is the one
   failure a casual test will not show.
4. **Each run has its own directory.** `runs/par-a-<host>-<stamp>-<pid>/` and `runs/par-b-…/` each hold
   their own `detect/`, `predictions.csv` and `metrics/`; neither contains the other's; `runs/latest`
   points at whichever run *started* last — the link is repointed after the pre-flight checks pass, not
   at the end — so here it is B, still training. Before run directories, B's start *deleted* A's in-flight
   checkpoints, because ultralytics' DDP launcher clears the save directory before spawning children.
5. **`SIGKILL` a run mid-training.** Its lease and entry survive briefly and then a waiter reclaims them
   after `auto_gpu.queue.stale_after_seconds` (120.0), with no human intervening. `cy-queue` shows the
   lease as `expired` in the meantime. The beat is per card: a run whose heartbeat is refused on one
   lease goes on beating the rest, so one unwritable file no longer ages that run's other cards out
   from under a live training. Only a lease that is gone, or one whose payload names another run,
   drops out of the beat.
6. **Both hydra output directories exist separately**, as `outputs/<date>/<HH-MM-SS>-<host>-<pid>`, each
   with its own log. Hydra resolves that path before any of this project's code runs, which is why the
   token is host-and-pid rather than the run id.

Then re-run sections 3 and 4 unchanged, to confirm `run_dir` broke neither artifact upload nor baseline
resolution.

## Overrides that matter on this box

`auto_gpu.batch_size=<n>` is the batch **per card**, used exactly as written — the only lever on batch
size left, and the way a verification run stays small on a GPU shared with CVAT and the ClearML server.
Unset, the batch is the largest one a run of this stage was seen to *finish* at on this model and this
card, read back from `~/.cache/clearml-yolo/batch_table.json`; before anything has finished there it is
`DEFAULT_BATCH`. Nothing scales a batch to a card's VRAM any more, so there is no denominator left to
raise the wrong way.

`auto_gpu.min_gpus` and `auto_gpu.max_gpus` are the floor and the ceiling on card count. One card is
`auto_gpu.max_gpus=1`; *exactly* two is `auto_gpu.min_gpus=2 auto_gpu.max_gpus=2`. Naming neither means
every free card, less what the runs already in the queue asked for.

`auto_gpu.wait_timeout_seconds=120` stops a run from blocking for the default 3600 s when another process
holds the card — **but only together with `auto_gpu.queue.enabled=false`**. At the shipped defaults the
run takes a place in the machine's queue instead, and a queued run waits with no deadline at all: the
timeout is read only on the no-queue path, so on its own it now buys nothing. Any verification run that
must fail rather than sit behind CVAT holding the card needs both overrides. The exception is section 5,
where the queue is the subject.

## Common mistakes

| Mistake | Reality |
|---|---|
| "`uv run pytest` passed, so the pipeline works" | The suite mocks the SDKs and never runs a stage for real. |
| Skipping `lint-imports` | It is the only check that catches a layering violation, and pre-commit will reject the commit. |
| Reading an empty `<run_dir>/reports` as failure | Expected with `report/baseline=none`. |
| `wait_timeout_seconds=120` on its own to bound a run | Unread at the shipped defaults; a queued run has no deadline. Add `auto_gpu.queue.enabled=false`. |
| `auto_gpu.max_gpus=2` to get *exactly* two cards | It is a ceiling. With one card free the run starts on one, because `min_gpus` is still 1. Exactly two is both keys naming 2. |
| `--force-gpu` to get past a queued peer in an ordinary verification run | It writes over the peer's lease and puts two trainings on one card. It is for a person who has decided that, not for making a test go. |
| `predict.output=` / `metrics.output_dir=` to redirect a `cy` run | They no longer compose. Use `run_dir=`. |
| `ultralytics.device=[0]` to get past a queued peer | A named device skips the *survey*, not the queue: it leases exactly the indices it names and refuses one a live peer lease covers. Deliberate sharing is `auto_gpu.queue.enabled=false`, and `auto_gpu.enabled=false` does not switch the leases off either. |
| Reaching for one blessed device spelling | `0`, `[0]`, `"0"`, `"0,1"` and `"cuda:0"` normalise to the same card, once, before any lease is taken, so the lease and the batch can no longer disagree about which card was meant. A spelling that names no card (`1.5`, `["cpu"]`, an empty list, a negative index) is refused by name with nothing leased. |
| `skip_predict=true` / `skip_metrics=true` to reuse a previous run's work in a fresh folder | Their consumers read the directory this run reads from: `runs/latest` when neither `run_id=` nor `run_dir=` was named, that named directory itself when either was. With the input absent the run refuses before training, naming the path. |
| Redirecting a standalone stage with `ultralytics.project=` and expecting `cy-predict` to follow | A `cy-train` told where to write moves no `latest` link, and the stages after it read that link. Leave `project` null and the run names its own directory. |
| A real directory sitting at `runs/latest` after `cy-metrics`/`cy-report` in a fresh folder | The next run moves it to `runs/latest-displaced-<host>-<pid>`, contents intact, and takes the name back as a symlink. Nothing to clear by hand, and nothing is deleted. |
| Running from a `conf/` dumped before `cy-predict`'s `weights` default became `null` | `cy-predict.yaml`'s `weights` is `null` now, meaning "the checkpoint this experiment's last training left". An old dump holds a literal `runs/latest/detect/yolo-run/…` that still composes, reads as a caller-named checkpoint and silently restores the old behaviour. Re-dump with `cy-init-config <dir> --force`. |
| First ClearML run warning "no completed task tagged prod" | Expected on a fresh project; compare needs a prior run. |
| Verifying against the real `clearml-yolo` project | Pollutes the `prod` baseline other runs resolve against. Use a throwaway project. |
| Treating `debug.ping` as proof ClearML works | It answers unauthenticated. Use `./scripts/check_env.sh`. |
