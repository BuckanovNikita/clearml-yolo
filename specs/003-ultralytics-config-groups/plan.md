# Implementation Plan: Native Ultralytics configuration groups

**Feature**: `003-ultralytics-config-groups` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

## Summary

Compose full shared native settings and sparse prediction overrides through Hydra; classify
stage applicability explicitly and serialize effective values over the original commented
native template. Preserve checkpoint, routing, task ownership and sanitization contracts.

## Technical Context

**Language/Version**: Python 3.12, runtime annotations and strict typing.

**Primary Dependencies**: Hydra/hydra-zen, OmegaConf, installed Ultralytics, ClearML,
Pydantic, Loguru; declare the selected comment-preserving YAML dependency directly.

**Storage**: Local YAML/manifests and existing ClearML configuration/artifact storage.

**Testing**: Focused pytest with controlled external substitutes, Ruff, mypy, import-linter,
and documentation/link checks. Heavy native/GPU/live ClearML checks were explicitly authorized
on 2026-09-28 and are recorded with their limits in
[verification-2026-09-28.md](verification-2026-09-28.md).

**Target Platform**: Existing supported Python environment; portable filesystem behavior.

**Project Type**: CLI and pipeline package.

**Performance Goals**: Config initialization and composition import neither Ultralytics nor Torch.

**Constraints**: Preserve dependency pins, one-task ownership, credentials protection and
existing model/calibration/output contracts. Publishing a release is outside scope.

**Scale/Scope**: Five model command interfaces, eight generated command files, two group files.

## Constitution Check

Pre-design: Principle III formerly mandated sparse/raw-file composition. The explicitly
authorized constitution 4.0.0 amendment resolves this incompatible change.

Post-design: Typed boundaries and deferred runtime imports remain; SDK access stays in adapters
and tasks. Native serialization has no ClearML dependency. Existing ownership, privacy and
verification requirements are retained. The initial user restriction deferred heavy checks; subsequent explicit authorization
allowed real-run verification. Only executed checks establish passing integration evidence.

## Project Structure

Feature documents live in `specs/003-ultralytics-config-groups/`: specification, research,
data model, contracts, quickstart, task list and requirements checklist.

Implementation remains in `src/clearml_yolo/`: shared native configuration support, Hydra
registration and example generation, task/inference integration, and existing ClearML adapters.
Tests remain in `tests/` alongside related configuration, task and artifact coverage.

## Implementation Changes

1. Resolve upstream default YAML using package metadata without importing model runtimes.
   Preserve its comments/order and define tested train/predict applicability for every key.
2. Register full shared defaults and inherited prediction settings; generated command defaults
   select root-key group files. Explicit prediction values override inherited values, including
   null/default values. Remove legacy file overlay and reject removed interfaces.
3. Resolve effective inputs at task/native boundaries. Filter stage-irrelevant settings,
   preserve internal training validation options, validate prediction batch, enforce owned
   checkpoint/output paths and shared comparison settings.
4. Export effective native YAML and persistent source manifests. Connect sanitized commented
   YAML through existing ClearML ownership and upload lifecycle; use split/role identifiers.
5. Update current contracts, Russian README and migration documentation. Verify focused
   behavior and static gates, then converge against requirements. Execute heavy checks only
   after explicit authorization and keep their outcomes in dated evidence.

## Complexity Tracking

No architectural exception is required. A shared native configuration module replaces
independently maintained sparse defaults and raw file precedence.
