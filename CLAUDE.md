# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
The machine-wide conventions in `/home/nkt/CLAUDE.md` (commit style, code style) still
apply; this file adds only what is specific to `clearml-yolo`.

## Project Overview

**clearml-yolo** is a set of composable hydra-zen apps for YOLO training, inference, metrics and model
comparison, tracked in ClearML. `cy` runs the whole pipeline; `cy-train`, `cy-predict`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth` and `cy-init-config` run the stages alone.

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
  report/baseline=none skip_compare=true auto_gpu.scale_to_vram=false auto_gpu.wait_timeout_seconds=120
```

`auto_gpu.scale_to_vram=false` pins the batch to the 24 GB `reference_vram_gb` rather than scaling to the
5090's 32 GB. At the shipped defaults it is defensive rather than load-bearing — `round_to_power_of_two`
floors the scaled batch back to the same number — but it holds if a run raises the anchor. The GPU is
shared with CVAT and the ClearML server; verification runs must not claim the whole card. Do not raise
`reference_vram_gb` to 32 to match the hardware; it is the denominator that sizes batches, not a memory
cap, so raising it *shrinks* the batch.

`report/baseline=none` is a group override, and it composes only against the packaged config. From a
`cy-init-config` folder the group is gone from the defaults list and the same thing is spelled
`report.baseline.source=none`.

## Architecture

**Layered**, enforced by import-linter (contracts in `pyproject.toml`):

```
apps → config_tree → configs → tasks → comparison → domain modules
```

A lower layer never knows about a higher one. `configs` sits **above** `tasks`, not below: it builds
configs from the task signatures themselves. Separate contracts keep the SDKs in place — `clearml` is
visible only to the `clearml_*` adapters and to tasks, hydra never reaches the domain modules, and
`ultralytics`/`torch` load only where weights are genuinely needed.

## Configuration

Hydra/hydra-zen. `cy-init-config` dumps a starting config tree; `uv run cy --config-dir conf
--config-name cy` runs from it. Without `--config-dir`, `cy` uses the packaged `pipeline` config.

Values more than one stage needs — `clearml`, `auto_gpu`, `ground_truth`, `splits`, `weights` — are named
once at the top level and **handed to each stage by the run itself**, in code, not by interpolation. A
stage block holds only what that stage alone decides. A config folder dumped before this change still
carries per-stage copies (`predict.weights`, `compare.iou_threshold`, …) that a run now recomputes and
silently overwrites — re-dump it. `predict.imgsz` is **not** one of them: it is deliberately absent from
`PIPELINE_FILLED_KEYS` (the reason is written out in the comment above that constant in
`tasks/pipeline.py`), so a stale copy fails composition instead of being overwritten.

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

**Change GPU/batch behaviour**: `gpu.py` decides devices and batch; `tests/test_gpu.py` pins each rung of
the ladder. Verify with a real run — the mocked suite cannot see a device it never allocates.

**Change what ClearML stores**: the adapters are `clearml_session.py`, `clearml_models.py`,
`clearml_report.py`; nothing else may import `clearml`. Verify against the server and confirm the
artifacts in the UI, per `running-end-to-end-tests`.
