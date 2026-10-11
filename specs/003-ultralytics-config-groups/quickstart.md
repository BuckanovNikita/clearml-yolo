# Validation quickstart

## Lightweight checks

Generate each selection into its own fresh directory with
`uv run cy-init-config DIRECTORY --command COMMAND`. Omission selects only `cy`.
Verify exactly one wrapper, plus both native groups for each of five model commands,
and no groups for the three non-model commands. Replace the shared group with the installed
upstream YAML. Compose all five model commands with `--cfg job` and ordinary shared/prediction
overrides; composition must not execute a model or create a task.

Run the affected focused pytest cases for configuration generation, Hydra composition, stage
filtering, checkpoint routing, commented export and mocked artifact publication. Run Ruff,
mypy and import-linter using the existing documented commands. Check Markdown paths and
`git diff --check`. Record exact executed commands/results in dated evidence.

Verify explicit prediction null/default values, inherited settings, invalid prediction batch,
removed interfaces, conflicts, group selection and file/parent/symlink collisions. With
isolated runtime substitutes, compare exported active settings to captured native arguments
and verify per-split/per-role sources still exist after prediction.

## Real-run checks (explicitly authorized on 2026-09-28)

Follow the project `running-end-to-end-tests` skill and applicable environment
skill using explicit project/tags, task-owned outputs and available inputs. Run training,
prediction and paired comparison, inspect the local requested/effective YAML, and compare its
active values with captured native arguments. Replay training and prediction using native Ultralytics `cfg=EXPORTED_YAML`
with the corresponding local dataset, model and manifest. Record dated real-run evidence.

Native replay's `cfg` belongs to the external Ultralytics command; it is intentionally forbidden
in clearml-yolo's wrapper interface. See [dated verification evidence](verification-2026-09-28.md) for executed checks and limitations.
