# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
The machine-wide conventions in `/home/nkt/CLAUDE.md` (commit style, code style) still
apply; this file adds only what is specific to `clearml-yolo`.

## Project Overview

**clearml-yolo** is a set of composable hydra-zen apps for YOLO training, inference, metrics and model
comparison, tracked in ClearML. `cy` runs the whole pipeline; `cy-train`, `cy-predict`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth` and `cy-init-config` run the stages alone. `cy-queue` is
the odd one out — an argparse `rich` TUI over the machine's run queue, composing no config at all.

**Language**: Python 3.12, Russian documentation (README.md only).

## Before any end-to-end work: check the environment

```bash
./scripts/check_env.sh
```

Reports whether `uv`, the local ClearML server, the GPU and `docker` are usable, and exits 0 either way.
A `SessionStart` hook (`.claude/settings.json`) runs it automatically and injects the result, so the
status is in context from the first message of every session — read it before planning a real run.

It checks ClearML with a real authenticated `auth.login`, not a ping. `debug.ping` answers **without any
credentials**, so a reachable server with a stale `~/clearml.conf` looks healthy right up to the moment a
run dies on `LoginError ... 401 ... (failed to locate provided credentials)`.

## Development Commands

All tools run via `uv run`:

```bash
# The full static suite — all four, in this order
uv run pytest              # mocked: no server, no GPU
uv run ruff check .        # lint (add --fix to auto-fix)
uv run mypy .              # type check, strict
uv run lint-imports        # architecture contracts from pyproject.toml

uv run pre-commit run --all-files   # the same four, plus the generic file hooks
```

`uv run pre-commit install` installs the hook. These four run through `uv run` out of the locked `dev`
group, so a hook and a hand-typed command are the same command against the same locked versions. The
hook also runs the upstream `pre-commit-hooks` set first (`check-yaml`, `check-toml`, merge conflicts,
file size, whitespace, end-of-file) — those come from a pinned remote repo in pre-commit's own
environment, not from `dev`.

**`lint-imports` is part of the suite**, not an extra. It is the check most often skipped and the only
one that catches a layering violation; pre-commit rejects the commit either way.

## Testing

The pytest suite needs **no server and no GPU** — it stubs `clearml`, `ultralytics` and `torch` per test,
in the tests that touch them. The one exception is deliberate: `tests/test_ultralytics_params.py` imports
the real `ultralytics.cfg`, because its job is to check the vendored parameter files against the
installed package. Either way the suite cannot catch a broken pipeline wiring, a stage that mis-handles a
device, or an artifact that never uploads. "The full tests" for this project means the static suite
**and** a real `cy` run.

**REQUIRED SKILL:** use `running-end-to-end-tests` for the real runs — it holds the verified offline
smoke command, the ClearML-backed command, how to exercise the compare stage, and what to check
afterwards. Use `running-clearml-server` for anything involving the server itself.

Shortest honest verification of a pipeline change, no server needed:

```bash
uv run cy clearml.enabled=false train.ultralytics.data=coco8.yaml train.ultralytics.epochs=1 \
  report/baseline=none skip_compare=true \
  auto_gpu.queue.enabled=false auto_gpu.wait_timeout_seconds=120
```

`auto_gpu.queue.enabled=false` is what makes `wait_timeout_seconds` mean anything. At the shipped
defaults the run takes a place in this machine's queue instead, and a queued run waits **without a
deadline** — the timeout is read only on the no-queue path. Leave the queue on when the point of the run
is the queue; switch it off whenever the run must fail rather than sit behind CVAT holding the card.

Nothing in the command sizes the batch, and that is now correct: the batch is the largest one a run of
this stage was seen to *finish* at on this model and this card, read from
`~/.cache/clearml-yolo/batch_table.json`, and `DEFAULT_BATCH` before anything has. The GPU is shared with
CVAT and the ClearML server, so a verification run that must stay small says
`auto_gpu.batch_size=<n>` — a batch **per card**, used exactly as written. There is no reference-VRAM
arithmetic left to get backwards.

`report/baseline=none` is a group override, and it composes only against the packaged config. From a
`cy-init-config` folder the group is gone from the defaults list and the same thing is spelled
`report.baseline.source=none`.

## Architecture

**Layered**, enforced by import-linter (contracts in `pyproject.toml`):

```
apps → config_tree → configs → tasks → comparison → domain modules → run_queue | run_identity
```

A lower layer never knows about a higher one. `configs` sits **above** `tasks`, not below: it builds
configs from the task signatures themselves. Separate contracts keep the SDKs in place — `clearml` is
visible only to the `clearml_*` adapters and to tasks, hydra never reaches the domain modules, and
`ultralytics`/`torch` load only where weights are genuinely needed.

`run_queue` and `run_identity` are the **bottom** layer, beneath `gpu` — pure filesystem, no NVML, no
ultralytics, no ClearML, no hydra. `gpu.wait_for_devices` imports `run_queue` and so cannot be imported
by it; siblings in one layer may not import each other either, which is why `run_identity` never reaches
for the queue. `queue_view` (the pure `render(state) -> Table`) sits one layer up beside `gpu`, and
`apps/queue.py` joins the "every app entrypoint stands alone" contract like the other entry points.

## Configuration

Hydra/hydra-zen. `cy-init-config` dumps a starting config tree; `uv run cy --config-dir conf
--config-name cy` runs from it. Without `--config-dir`, `cy` uses the packaged `pipeline` config.

Values more than one stage needs — `clearml`, `auto_gpu`, `ground_truth`, `splits`, `weights`, `run_id`,
`run_dir` — are named once at the top level and **handed to each stage by the run itself**, in code, not
by interpolation. A stage block holds only what that stage alone decides. A config folder dumped before
this change still carries per-stage copies (`predict.weights`, `compare.iou_threshold`, …) that a run now
recomputes and silently overwrites — re-dump it. `predict.imgsz` is **not** one of them: it is
deliberately absent from `PIPELINE_FILLED_KEYS` (the reason is written out in the comment above that
constant in `tasks/pipeline.py`), so a stale copy fails composition instead of being overwritten.

`run_id`/`run_dir` are the same kind of value and they moved every output path with them: `predict.output`,
`metrics.output_dir`, `report.output_dir` and `compare.output_dir` joined `PIPELINE_FILLED_KEYS`, so a
dump that predates them **fails composition** (`Key 'output' not in 'Config'`) rather than being silently
overwritten — re-dump with `cy-init-config <dir> --force` after any change to that constant. The one
output key that still composes is `train.ultralytics.project`: it lives in the shared ultralytics file and
so cannot be dropped, and the run overwrites it with `<run_dir>/detect` (the comment above
`PIPELINE_FILLED_KEYS` says why). To redirect a whole run, set `run_dir=`, never a stage's own path.

`run_id`/`run_dir` also decide which directory a *skipped* stage's consumer reads:
`_resolve_run_directories` hands `stage_configs` this run's own directory when the caller named either
key, and `runs/latest` (resolved before the run repoints it) only when it named neither. Naming a
directory means re-entering it, so `run_dir=<path> skip_metrics=true` reports against the dashboards
that path holds and refuses naming it when there are none. The standalone default checkpoint is the
matching case one layer out: `_predict_fields()["weights"]` is `None`, and `predict.checkpoint_of_last_training`
resolves it at run time from **this** run's `clearml.task_name` under `runs/latest`, refusing before
`init_task` when nothing trained there. A dump that predates that still carries the literal path, which
composes, reads as a caller-named checkpoint and silently restores the old behaviour — re-dump.

Every ultralytics parameter lives in `src/clearml_yolo/conf/ultralytics/`, one file per stage, each
listing the whole of ultralytics' configuration. `null` there means "leave ultralytics' own default
alone". A `cy-init-config` dump copies these to `<dir>/ultralytics/`; repo-root `conf/` is such a dump
and is untracked.

## ClearML

The server is a **machine-level service shared with other work**, not part of this repo:
`/home/nkt/clearml-server`, UI on 8580 (CVAT's traefik owns 8080), API on 8008, files on 8081.
Credentials in `~/clearml.conf` (gitignored). Never `docker compose down` a stack you did not start.

Two facts that have cost time before:

- **ClearML model metadata carries no label enumeration.** Class names must come from the checkpoint, not
  from ClearML metadata.
- **Dashboard thresholds are rounded.** For exact per-class thresholds read the
  `metrics_best_confidences_<split>` artifact, not the dashboard. (`best_confidences` is the in-process
  field name; the artifact names are all built in `artifact_names.py`.)

## Important Files

- **README.md** — user documentation (Russian), including the batch-sizing ladder and compare workflows
- **pyproject.toml** — dependencies, tool configs, import-linter contracts
- **scripts/check_env.sh** — environment readiness check, also run by the SessionStart hook
- **.claude/skills/** — `running-clearml-server`, `running-end-to-end-tests`

## Common Tasks

**Add a pipeline stage**: add the task under `tasks/`, register its config in `configs` (built from the
task signature), expose an app in `apps/`, then extend `PIPELINE_FILLED_KEYS`/`stage_configs` so the run
hands it the shared values. Add the parity case to `tests/test_configs.py`.

**Change GPU/batch behaviour**: `gpu.py` decides devices and batch; `tests/test_gpu.py` pins each rung.
How many cards a run takes is `auto_gpu.min_gpus` (the floor it will not start below) and
`auto_gpu.max_gpus` (the ceiling); an *exact* count is both of them naming the same number, and a run
with no ceiling takes every free card less what the runs already waiting asked for. That cap, and the one
poll a greedy run waits before it claims, are the whole of what stops the first run swallowing a machine.
Neither can take a card back out of a running DDP job, so a planned split is still two runs each naming
`min_gpus`/`max_gpus`. Verify with a real run — the mocked suite cannot see a device it never allocates.

`auto_gpu.force=true`, spelled `--force-gpu` on the command line, is past all of it: no queue, no wait,
no guards, and other runs' leases written over. It can put two trainings on one card. It is the only
caller of `RunQueue.seize_leases`, which is the only write in `run_queue.py` that is not an `O_EXCL`
create.

**Change the queue or the run directory**: `run_queue.py` owns the lease and entry files and the pure
`order()`; `gpu._wait_in_turn` is the whole scheduler (there is no daemon — the waiting `cy` process is
it), and it reads the entries **before** the survey, which is what stops a fresh run jumping the line the
instant a card frees. `run_identity.py` names the run and repoints `runs/latest`, moving anything at
that name that is not a symlink to `runs/latest-displaced-<host>-<pid>` with its contents rather than
freezing the workspace on it or deleting it; `tasks/pipeline.py`
hands `run_dir` to every writing stage, and `tasks/train.py` mints the same identity for a standalone
`cy-train`, which is why the other standalone apps compose their paths through `runs/latest`.
`tests/test_run_queue.py`, `tests/test_run_identity.py`, `tests/test_queue_view.py`,
`tests/test_queue_app.py` and `tests/test_gpu.py` cover more of this than usual, because the queue is
pure filesystem and points at `tmp_path`. What they still cannot see is two processes racing one card, so
verify with the two-terminal run in `running-end-to-end-tests`. Settings nest as `auto_gpu.queue.*`
rather than sitting beside `auto_gpu`, so the three stages already handed `auto_gpu` need no new
parameter and neither parity test gains an entry.

`leases/` holds two kinds of file. `gpu-<index>` is a lease — the file **is** the lock. `.reclaim-gpu-<index>-<inode>-<mtime_ns>` is a
transient marker naming the exact lease generation a run is taking over, created with `O_EXCL` so that of
everyone who read the same stale lease exactly one may replace it. A marker is not a held card and not a
leak: `_gpu_index_of` and `apps/queue.py::_lease_files` both filter it out by prefix, a reclaim removes
its own on every exit path, and one orphaned by a killed reclaimer is dropped by the next reclaim once it
is older than `stale_after_seconds` — so an aged marker is the recovery working, not a stuck card. Never
count one as a lease, never clear one by hand, and never sweep `leases/` of anything but `gpu-*`.

**The marker is not an airtight mutex, and the aged drop is where it gives way.** Read
`_take_over_a_stale_lease` before touching either. Removing a marker is a decision and then an unlink,
two calls no name on a POSIX filesystem joins — a tomb, a second marker, or a liveness check on the
owner each reproduce the same gap one level down, which is why the primitive is not rebuilt. The
sequence: a reclaimer killed between creating its marker and replacing the lease leaves an aged marker;
two later runs both read it as aged; one unlink lands, a third run creates the marker afresh and enters
the critical section, and the other run's delayed unlink takes *that* marker away, admitting a fourth
reclaimer of the same generation. Both replace the lease and both believe they hold the card. Across
users the loser is told, at its next refused beat; **between two runs of one user the beat lands on the
winner's file and the double hold is silent** until the two trainings collide in VRAM. Reaching it needs
a kill inside the gap between two adjacent syscalls, an unlink delayed past a whole second reclaim, and
two further runs racing that same dead generation.
`_drop_a_marker_its_reclaimer_died_holding` re-reads the generation immediately before the unlink and
only unlinks the inode and heartbeat it judged aged, which narrows the decision-to-removal gap to one
stat and one unlink — it does not close it, because a cached attribute on a shared mount can answer the
re-read from before the change.

The heartbeat is per card, and a refused beat on one lease no longer ends the beat for the rest: a card
is dropped from `_beat_until`'s list only on positive evidence it stopped being this run's — the file is
gone, or the write was refused *and* the payload names another run. Any other refusal keeps the card in
the beat and warns once per beat, because dropping a card the run still holds is the harm the beat
exists to prevent, while beating a card that really is lost costs a log line. `heartbeat_entry` follows
the same rule: only a missing file means cancelled, so a refused write leaves the waiter waiting rather
than reporting a cancellation nobody asked for.

**Change what ClearML stores**: the adapters are `clearml_session.py`, `clearml_models.py`,
`clearml_report.py`; nothing else may import `clearml`. Verify against the server and confirm the
artifacts in the UI, per `running-end-to-end-tests`.
