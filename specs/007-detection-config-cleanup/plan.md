# Implementation Plan: Detection configuration cleanup

**Branch**: `007-detection-config-cleanup` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Separate example presentation from runtime native YAML, resolve default filesystem roots
from adapter-provided task identity, and publish consolidated evidence for selected splits.
Preserve feature 006 publication and all pinned dependencies.

## Technical Context

Python 3.12 CLI; existing Hydra/hydra-zen, Pydantic, ClearML, Ultralytics,
digital-metrics and FiftyOne dependencies. Filesystem output plus ClearML artifacts and
FiftyOne storage. Existing pytest, Ruff, mypy, import-linter and pre-commit tooling.
No performance algorithm changes or new dependencies. Scope: eight execution commands,
two native groups, three default evaluation splits.

## Constitution Check

Before and after design: passes typed Python, adapter boundaries, configuration/run ownership,
proportional verification and collaboration constraints. Runtime records remain complete;
example commenting does not weaken composition. No dependency or constitution amendment.

## Project Structure

- src/clearml_yolo/native_config.py, config_tree.py, configs.py: examples/defaults.
- src/clearml_yolo/clearml_session.py, run_identity.py, apps/common.py: identity/routing.
- src/clearml_yolo/tasks/{pipeline,train,predict,val,metrics}.py: stage integration.
- src/clearml_yolo/artifact_names.py: per-split inventory.
- tests/: configuration, routing, metrics and publication regression tests.
- specs/007-detection-config-cleanup/: specification, research, contracts and task ledger.
- docs/evidence/: portable dated acceptance evidence; machine details stay in global skill.

## Implementation Sequence

1. US1: failing composition/example tests, device defaults, example-only sections.
2. US2: failing identity/routing tests, safe filesystem helper and ClearML adapter,
   CLI and direct-call routing. Preserve explicit precedence and stage layout.
3. US3: selected-split tests, consolidated workbooks, one validation-threshold CSV,
   defaults/fallbacks and failure paths.
4. Update documentation; run gates, real isolated acceptance and fresh-context review.

## Review Focus

Example comments must not delete registered Hydra keys or runtime-derived values.
Explicit routing must not need fake/default task identity. Unsafe task names cannot create
nested native paths. Workbook construction must enforce required local diagnostics even
outside a tracked invocation.
Publication must preserve exact matching and dataset reuse when roots differ.
