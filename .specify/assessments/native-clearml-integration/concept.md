# Concept: Native ClearML tracking

- **Slug**: native-clearml-integration
- **Created**: 2026-09-30
- **Recommended option**: complete native reporting and preserve publication contracts

## Options

### Option A — Preserve current behavior

- **Sketch**: keep final-only DDP progress and existing configuration/model publication.
- **Appetite**: small, no feature delivery.
- **Trade-offs**: minimal risk but leaves the user's live progress requirement unmet.
- **Rabbit holes**: none.

### Option B — Complete native reporting and preserve publication contracts

- **Sketch**: show native epoch reporting during distributed training; protect existing best-model and configuration recovery guarantees with behavior and real-run evidence.
- **Appetite**: small (days), a scope budget rather than a completion estimate.
- **Trade-offs**: satisfies the user without redefining upstream metrics; requires careful failure and publication ownership handling.
- **Rabbit holes**: historical cleanup and dependency replacement would expand scope and are excluded.

### Option C — Custom tracking and artifact architecture

- **Sketch**: replace native reporting with a project-owned telemetry and replay implementation.
- **Appetite**: medium (weeks), assumption.
- **Trade-offs**: broader control but duplicates existing native behavior and increases compatibility risk.
- **Rabbit holes**: batch telemetry, dashboards and storage redesign.

## Recommendation

Option B addresses the observed DDP gap while preserving guarantees already established by v0.10.0.

## Out of Scope

Historical deletion, custom batch telemetry, dependency updates, releases and shared-service intervention.

## Assumptions to Validate

The installed native callbacks remain the reporting authority; actual backend events and artifact inventories require real-run acceptance.
