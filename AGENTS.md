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

Nine entrypoints: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth`, and `cy-init-config`.
`cy-init-config DIRECTORY [--force]` writes editable examples for the eight execution
commands without creating a ClearML task. `cy-queue` remains removed.

Native model settings use top-level Hydra groups `ultralytics` and `ultralytics_predict`
for all model commands. The shared group covers detection-relevant installed upstream defaults; prediction
inherits applicable values through visible configuration references, preserving explicit nulls
and overrides. Prediction execution reads only its resolved group. Project defaults are
imgsz=960, compile=true and nms=true; prediction uses conf=0.001, batch=1, rect=true and
save=false. Native normalization is recorded separately from requested values.
Generated `ultralytics/default.yaml` and `ultralytics_predict/default.yaml` contain native
keys without wrapper indentation and preserve original comments. Use ordinary overrides
such as `ultralytics.epochs=10` and `ultralytics_predict.batch=8`.
Stage-irrelevant settings are commented in exported native YAML and excluded from execution.
Raw `cfg` loading, non-null native `cfg`, nested stage-native mappings and duplicate native
comparison inference settings are removed and must fail with migration guidance.
Effective native YAML and retained prediction manifests support replay; YAML is retained
locally with comments preserved; canonical run/dataset/report configurations and native General
parameters support ClearML replay without artifact copies.
Pass device, batch, AMP, compilation and native augmentation options directly to Ultralytics.

The project no longer provides GPU scheduling, filesystem queues or leases, batch tuning,
custom augmentation JSON, `--force-gpu`, or disabled tracking. Removed options must fail
rather than be silently ignored.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for test. A comparison
runs baseline and candidate on identical current test images and consumes their paired
current-test results from `comparison_dir`. Historical dashboards are not comparison input.
The automatic baseline is the latest completed prod-tagged task excluding the current task;
missing automatic baseline skips comparison, while invalid explicit references fail.

ClearML is required for execution commands. One execution invocation owns exactly one task;
nested stages reuse it and workers do not create tasks or upload artifacts.
Complete a task only after all required artifacts and the native best Output Model
are uploaded, verified and flushed. Fail task and command on computation, upload, flush, or interruption
errors while retaining local output. Never capture credentials. Native owner-only training/validation image previews are permitted.
Use the shared CSV-addressed dataset cache outside run outputs; source images are immutable.

## External dependencies

`digital-metrics` and `report-generator` live in `external/` as Git submodules.
Both track upstream `main` through `.gitmodules`; `git submodule update --remote`
advances their checkouts when an upstream update is requested.
Initialize them with `git submodule update --init --recursive` before `uv sync`.
Local development installs them editable through `[tool.uv.sources]`; the parent
repository's gitlinks pin their revisions. For installations without submodules,
users can select Git URLs and branches as documented in README.md. Git sources use
`branch = "main"` (or `master` for a user-selected repository); `uv.lock` records
the resolved commits.

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
