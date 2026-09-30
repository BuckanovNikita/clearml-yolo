# Problem Definition: Native ClearML tracking

- **Slug**: native-clearml-integration
- **Created**: 2026-09-30
- **Inputs used**: intake.md, research.md, approved conversation

## Problem Statement

Users cannot inspect distributed training progress while training runs because tracking events are delivered only after completion. Configuration and diagnostic clutter must not obscure performance evidence or become necessary for reproducing model runs.

## Affected Users & Stakeholders

- **Users**: training operators inspecting losses, validation, models and comparisons.
- **Stakeholders**: repository user approving this change and maintainers preserving replay guarantees.

## Goals

- Visible epoch progress before training finishes.
- One verified, usable best model per successful training invocation.
- Performance-only artifacts and configuration-backed recovery.

## Non-Goals

Historical task deletion, custom batch telemetry, dependency updates, GPU scheduling, commit, push and release.

## Success Metrics

- At least one completed epoch is visible before a multi-epoch run finishes (DDP baseline: unavailable).
- Exactly one best Output Model with matching downloaded bytes (existing guarantee to preserve).
- Zero configuration or diagnostic artifacts in new acceptance runs.
- Configuration replay and frozen-threshold paired comparison succeed without configuration artifacts.

## Cost of Inaction

DDP users continue waiting until completion to inspect their run; without explicit regression coverage publication and replay behavior may drift.

## Open Questions

No blocking intent questions. Execution availability is a verification limitation to record rather than invent.
