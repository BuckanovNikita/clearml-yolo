# clearml-yolo

`clearml-yolo` is a Python 3.12 set of Hydra/hydra-zen applications for YOLO
training, prediction, metrics, reports, and model comparison. `cy` runs the
pipeline; `cy-train`, `cy-predict`, `cy-metrics`, `cy-report`, `cy-compare`,
`cy-ground-truth`, and `cy-init-config` run individual stages. `cy-queue` is
an argparse/Rich queue viewer and does not compose Hydra configuration.

Keep user-facing README text in Russian. Keep code comments and log messages in
English.

## Route work deliberately

- For a real pipeline run, GPU allocation, a queue check, ClearML artifacts, or
  a baseline comparison, load `running-end-to-end-tests`.
- For which ClearML a run talks to, its credentials, or a LoginError 401, load
  `running-clearml-server`: the target is the shared ClearML stand on the
  cluster, never the user's own ClearML on this host.
- For a run of your own against the shared ClearML stand, follow
  [Agent runs](#agent-runs) below: `source scripts/agent_env.sh <slug>` first,
  `scripts/agent_cleanup.sh` last.
- Read `pyproject.toml` for the current commands, dependency constraints, and
  import-linter contracts. The mocked suite does not establish that a pipeline
  can train, use a GPU, or upload artifacts.

## Project contracts

Import layers are enforced by `lint-imports`:

```
apps -> config_tree -> configs -> tasks -> comparison -> domain modules -> run_queue | run_identity
```

`configs` builds task configuration and remains above `tasks`. Keep ClearML SDK
access in the ClearML adapters and tasks; `run_queue` and `run_identity` remain
filesystem-only bottom-layer modules.

Shared pipeline values (`clearml`, `auto_gpu`, `ground_truth`, `splits`,
`weights`, `run_id`, and `run_dir`) are handed to stages by the pipeline. Set
`run_dir` to redirect a pipeline run; stage output paths are not reliable
pipeline overrides. Use `cy-init-config` to create an editable config tree and
recreate a generated tree when its composition schema becomes stale.

`auto_gpu.force=true` (or `--force-gpu`) bypasses queueing and GPU safety
guards, including lease protection. Do not use it for ordinary verification.
With the normal queue enabled, a run waits in the filesystem queue without a
deadline unless `auto_gpu.queue.wait_timeout_seconds` names one; with it
disabled, `auto_gpu.wait_timeout_seconds` bounds the wait.

## Proportional verification

For a documentation-only change, validate the changed Markdown and referenced
paths. For code or commit work, choose relevant repository gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

The `tests/test_ultralytics_params.py` test intentionally imports the installed
Ultralytics configuration; other tests may stub ClearML, Ultralytics, or Torch.
Use the end-to-end skill when a change needs evidence beyond those static or
mocked checks.

## ClearML facts

An agent's runs go to the shared ClearML stand (`clearml.k8s.localhost`) as
the project `clearml-yolo`; `running-clearml-server` says how to become that
identity and points at the k8s-infra stand reference for the rest. The stand
is deployed and torn down by k8s-infra, never from this project, and the
user's own ClearML on this host is not a target for agents.

ClearML model metadata does not enumerate labels; obtain class names from the
checkpoint. Dashboard confidence thresholds are rounded; use the
`metrics_best_confidences_<split>` artifact for exact per-class values.

## Agent runs

An agent's `cy` run acts as the project `clearml-yolo` on the shared ClearML
stand, under one run tag, in one directory of its own. The scripts do the
contract's steps so nobody types them:

```bash
source scripts/agent_env.sh <slug>   # room preflight, stand credentials, INFRA_RUN_TAG, CY_RUN_TAG, CY_RUN_DIR
uv run cy auto_gpu.queue.wait_timeout_seconds=1800 auto_gpu.max_gpus=1 \
    run_dir=$CY_RUN_DIR clearml.project_name="$CY_RUN_TAG clearml-yolo" clearml.tags=[$CY_RUN_TAG] ...
scripts/agent_cleanup.sh             # clearml.py cleanup --prefix $CY_RUN_TAG, ls to prove it, rm -rf $CY_RUN_DIR
```

- `agent_env.sh` is sourced, not run. It refuses (returns 3) when `room` says
  WAIT, and exports nothing when the Secret or the mint is refused; the run
  line it prints is the one above with the tag filled in. An `INFRA_RUN_TAG`
  already exported (minted with `--keep`, say) is kept as is.
- GPU: the cap is `[capacity].gpu_runs` in the registry; training runs on the
  host GPU through this project's own filesystem queue, always with
  `auto_gpu.queue.wait_timeout_seconds` set so an unattended run fails rather
  than blocks, and never with `--force-gpu`. Never enqueue a task on the
  stand's `CLEARML_QUEUE`: its task pods are CPU-only and cannot reach the GPU.
- The ClearML SDK reads `CLEARML_API_HOST` and the key pair from the
  environment before `~/clearml.conf`; that is why the sourced exports are
  enough and why `scripts/check_env.sh` reports which endpoint it authenticated
  against and warns when it is the user's host stand on `localhost:8008`.
- Clean up on success and on failure. `agent_cleanup.sh` removes the run
  directory only when it is named after the tag; anything kept on purpose is
  reported by its full name.

## Shared infra

This project is `clearml-yolo` in the k8s-infra registry and may use the shared
stands `clearml` on the docker-desktop cluster as identity `clearml-yolo`. The
skill is `/mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra` (its `projects.toml` is the registry); read its
`references/run-contract.md` before touching a stand.

- Preflight: `python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/infra.py room`; obey WAIT (exit status 3).
- Mint one tag per run and export it (assign, then export, so a refused mint
  stops you instead of exporting an empty tag):
  `INFRA_RUN_TAG=$(python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/infra.py newtag --project clearml-yolo --slug <what>) && export INFRA_RUN_TAG`
  Not Claude Code? Export `INFRA_HARNESS=codex|ci|human` first; the default is `claude`.
- Name everything you create by `$INFRA_RUN_TAG` as the stand reference says.
- Credentials come from the helpers, never from files:
  `eval "$(python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo env)"`
- Clean up on success and on failure, then prove it with `ls`:
  `python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo cleanup --prefix "$INFRA_RUN_TAG"`
- Caps are `[capacity]` keys in `/mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/projects.toml`: `sandbox_runs_soft`
  bounds every run, `cveta2_integration_runs` the cveta2 suites, `gpu_runs` the
  trainings, `lakefs_heavy_runs` the lakeFS-heavy runs; `room` enforces
  `max_pods_soft`, `fat_stand_max` and `clearml_max_task_pods`.
- Never run `cleanup --stale` without `--dry-run`. Never touch another tag or a
  durable name. Report anything intentionally kept by its full name.
