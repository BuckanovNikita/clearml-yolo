# Implementation Plan: clearml-yolo 0.3.0

**Branch context**: existing checkout; feature selected by `.specify/feature.json`
**Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

## Summary

Remove custom model runtime automation. Keep native model argument mappings sparse so
presence, never comparison with defaults, determines precedence. Preserve evaluation and
comparison mathematics while replacing historical report inputs with current-test outcomes.
Centralize invocation tracking with nested stage reuse and synchronous artifact checks.

## Technical Context

**Language/Version**: Python >=3.12,<3.13, strict mypy and Ruff as configured.
**Primary Dependencies**: Ultralytics, Hydra/hydra-zen, Pydantic, ClearML, digital-metrics,
report-generator, pandas, scipy, openpyxl, Loguru; exact constraints in pyproject.toml.
**Storage**: isolated local run directory plus required ClearML artifacts; images external.
**Testing**: pytest, Ruff, mypy, import-linter, pre-commit, real integration runs, package install.
**Target Platform**: Linux, CPU and GPU execution; native DDP contract tests.
**Project Type**: CLI package with eight commands.
**Performance Goals**: native execution without custom scheduling/tuning overhead; correctness
and reproducibility are release gates, not a new latency promise.
**Constraints**: no new service, no registry publication, no shared-resource teardown.
**Scale/Scope**: existing detection datasets and workbook contracts; unchanged external tables.

## Constitution Check

Before research and after design: PASS against constitution 2.0.0. Preserve strict checks,
Loguru, clear module boundaries, explicit external-library adapters, isolated outputs, one
task and upload completion, validation-only calibration, environment-specific preflight/capacity and
cleanup. This release intentionally updates import contracts for removed modules and new val.
No weakened checks or undocumented exceptions are planned.

## Project Structure

- src/clearml_yolo/configs.py: sparse configuration registration and raw-YAML overlay.
- src/clearml_yolo/apps/: eight independent CLIs and common invocation adapter.
- src/clearml_yolo/tasks/train.py, predict.py: native execution and actual result paths.
- src/clearml_yolo/tasks/val.py: prediction and frozen evaluation of a checkpoint.
- src/clearml_yolo/tasks/pipeline.py: ordered composition, output ownership and shared task.
- src/clearml_yolo/tasks/metrics.py, compare.py, report.py: shared evaluated results.
- src/clearml_yolo/comparison/: retained statistics and workbook builders.
- src/clearml_yolo/clearml_session.py, clearml_models.py: lifecycle, manifest and model lookup.
- src/clearml_yolo/inference.py: image manifest/table conversion, no hardware automation.
- tests/: focused contract tests plus retained domain regressions.
- docs/migration-030.md, docs/evidence/: migration and dated release acceptance evidence.
- .claude/skills/running-end-to-end-tests/: portable verification; machine helpers live in a global environment skill.

## Phases and decisions

1. Record release intent, contracts and dependency-ordered tasks; analyze coverage.
2. Implement sparse native configuration and remove runtime automation. Keep default model
   selection as a minimal example; upstream owns runtime defaults. Use +ultralytics.key=value
   to add a previously absent key; existing embedded keys accept ordinary Hydra overrides.
3. Implement tracking owner boundary around all CLI invocations. Nested tasks call init_task
   to reuse the owner. Disable native ClearML integration before model imports and in workers.
   Synchronously upload named artifacts and keep a required manifest, fail on missing/rejected
   uploads, wait for pending SDK work before completion. Sanitize configuration secrets.
4. Calibrate candidate once on val; score requested splits at that frozen mapping. Build shared
   current-test baseline/candidate dashboards and statistical outcomes under the same settings.
   Report generation consumes these evaluated dashboards and never fetches historical ones.
5. Integrate pipeline and cy-val, validate skip-stage input paths and output conflicts. Compare
   produces reusable report inputs even if workbook rendering runs as a separate stage.
6. Delete obsolete source/tests/docs within the requested removal inventory; preserve unrelated
   untracked directories. Update package contracts, examples, helpers and migration notes.
7. Run all static/regression gates, CPU/GPU acceptance, artifact download and failure checks,
   package builds/install/help checks. Converge against artifacts and close any appended tasks.

## Dependencies and ownership

Tracking adapters are independent of evaluation implementation. Evaluation owns metrics,
comparison/report tasks and comparison helpers. Parent owns configs, apps, train/predict,
pipeline/val integration, removals, packaging and docs. Interfaces are detailed in contracts/.
All writers run focused checks; the parent runs complete gates and a fresh read-only review.
