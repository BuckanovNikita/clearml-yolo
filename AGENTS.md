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

## External dependencies

`digital-metrics` is an external dependency. Keep it pinned to the approved upstream
revision. Do not change its source, checkout, dependency reference or locked revision
without the user's explicit intent to change that dependency. General implementation,
cleanup and dependency maintenance requests do not authorize such changes. Adapt
`clearml-yolo` integration code when compatibility work is needed; report upstream
issues instead of patching or monkeypatching the dependency.

## Project and environment guidance

- Read `pyproject.toml` for entrypoints, dependencies and import contracts.
- Public CLI and artifact contracts live in `specs/001-release-030/contracts/`.
- For integration verification, load the project skill `running-end-to-end-tests`.
- Machine-specific endpoints, credentials, capacity, run helpers and local execution
  records belong in global environment skills. When available, load
  `clearml-yolo-environment` for this project's local integration environment.
  Other installations should use their own environment instructions.
- Pass ClearML project names and tags explicitly. Application configuration must not
  depend on an agent harness or a particular machine.
