# Personal engineering instructions

## Working agreement

Carry the requested outcome through implementation and appropriate verification.
Inspect relevant code, configuration, and existing changes before editing. Treat plans
and task files as intent and the current repository as implementation evidence. Preserve
unrelated work. Ask only for information that materially changes the result and cannot
be discovered in the repository.

For a bug, capture and reproduce the failing observation when feasible. Verify the
original failure path after the fix. Report checks and limitations accurately.

## Verification and collaboration

Use the repository's documented tooling and current check configuration. For code or
commit work, select the affected gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

Documentation-only work needs Markdown and link validation, not an unrelated application
suite. The mocked suite cannot prove native training, a GPU, or ClearML uploads. Do not
claim those outcomes without dated real-run evidence.

Track processes and temporary resources created by this task and clean them up. Leave
pre-existing shared services, containers, and data intact.

## Python preferences

Follow the existing toolchain. Prefer strict types, explicit access, Loguru for application
logging, and Pydantic for validated configuration. Catch exceptions at a boundary that can
handle them, using specific types where practical. Keep code comments and log messages in
English.

## Git and documentation

Commit only when requested. Stage explicit paths or hunks belonging to the task; preserve
unrelated staged and unstaged changes. Do not stash, reset, revert, or bypass hooks to make
a check pass. Use Conventional Commits when committing.

Write README.md in Russian. Write other documentation, skills, and instruction files in
English unless the user or project states otherwise. Keep observed test counts, timings,
and deployment status in dated evidence rather than evergreen documentation.

--- project-doc ---

# clearml-yolo

`clearml-yolo` is a Python 3.12 group of Hydra/hydra-zen applications for native
Ultralytics YOLO training, prediction, validation, metrics, reports, and model comparison.
`cy` runs the pipeline; `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, and `cy-ground-truth` run individual stages.

## Project contracts

Eight entrypoints remain: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, and `cy-ground-truth`. `cy-queue` and `cy-init-config` are
removed.

Native model settings are sparse `ultralytics` mappings: `train.ultralytics` and
`predict.ultralytics` in the pipeline. A neighbouring `cfg` names unchanged native YAML.
Precedence is native defaults, cfg YAML, the explicitly supplied embedded mapping, then
Hydra CLI overrides. Add an absent setting with `+ultralytics.key=value` (or
`+train.ultralytics.key=value`); override an existing setting without `+`. Pass device,
batch, AMP, compilation, and native augmentation options directly to Ultralytics.

The project no longer provides GPU scheduling, filesystem queues or leases, batch tuning,
custom augmentation JSON, configuration-tree generation, `--force-gpu`, or disabled
tracking. Removed options must fail rather than be silently ignored.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for test. A comparison
runs baseline and candidate on identical current test images and consumes their paired
current-test results from `comparison_dir`. Historical dashboards are not comparison input.
The automatic baseline is the latest completed prod-tagged task excluding the current task;
missing automatic baseline skips comparison, while invalid explicit references fail.

ClearML is required. One invocation owns exactly one task; nested stages reuse it and workers
do not create tasks or upload artifacts. Complete a task only after all required artifacts
are uploaded and flushed. Fail task and command on computation, upload, flush, or interruption
errors while retaining local output. Never capture credentials or dataset images.

## Route work deliberately

- For a real pipeline run, GPU use, ClearML artifacts, or a baseline/candidate comparison,
  load `running-end-to-end-tests`.
- For ClearML endpoint, credentials, or LoginError 401, load `running-clearml-server`.
  Agent runs target the shared stand, never the user's host ClearML.
- Read `pyproject.toml` for installed entrypoints, dependency constraints, and import-linter
  contracts. Read the CLI and artifact contracts in `specs/001-release-030/contracts/` when
  changing public behaviour.

## Agent runs

An agent run uses the shared ClearML stand as project `clearml-yolo`, under one tag and in
one directory. Do not perform stand operations unless the task requires a real run. Before
minting a tag outside an environment that already supplies it, set `INFRA_HARNESS=codex`.

```bash
source scripts/agent_env.sh <slug>
uv run cy run_dir=$CY_RUN_DIR \
    clearml.project_name="$CY_RUN_TAG clearml-yolo" clearml.tags=[$CY_RUN_TAG] \
    +train.ultralytics.device=0 +predict.ultralytics.device=0 ...
scripts/agent_cleanup.sh
```

- `agent_env.sh` is sourced and returns 3 when `room` says WAIT. It exports no run tag when
  credential retrieval or minting fails. It preserves a pre-exported `INFRA_RUN_TAG`.
- `run_dir` keeps agent output outside the checkout. Native `device=0` selects the host GPU;
  no project GPU queue or force option exists.
- The ClearML SDK reads its endpoint and key pair from the environment before
  `~/clearml.conf`; `scripts/check_env.sh` reports the authenticated endpoint and warns when
  it is the user's host stand.
- Always clean up on success and failure. `agent_cleanup.sh` calls tag-scoped cleanup, proves
  it with `ls`, and removes a directory only when its name is the tag.

## Shared infra

This project is `clearml-yolo` in the k8s-infra registry and may use the shared `clearml`
stand on the docker-desktop cluster. Read
`/mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/references/run-contract.md` before touching a
stand.

- Preflight with `python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/infra.py room`
  and obey WAIT (exit status 3).
- Mint exactly one tag per real run:
  `INFRA_RUN_TAG=$(python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/infra.py newtag --project clearml-yolo --slug <what>) && export INFRA_RUN_TAG`.
- Obtain credentials only through
  `eval "$(python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo env)"`.
- Clean up only the run's tag and prove it:
  `python3 /mnt/wsl/data/nkt/k8s-infra/skills/k8s-infra/scripts/clearml.py --project clearml-yolo cleanup --prefix "$INFRA_RUN_TAG"`, then `ls` with the same prefix.
- Capacity is maintained in the registry's `[capacity]` values. `room` enforces the shared
  soft limits. Never use stale cleanup without `--dry-run`, touch another tag, or delete a
  durable name.
