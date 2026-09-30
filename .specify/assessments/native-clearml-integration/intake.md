# Idea Intake: Native ClearML tracking

- **Slug**: native-clearml-integration
- **Created**: 2026-09-30
- **Source**: user conversation and current repository
- **Type**: improvement

## Idea (as captured)

> Ultralytics default ClearML integration must be fully enabled. Show loss and training progress in plots/scalars and save the best model as Ultralytics does by default. Artifacts may contain only weights or data useful for model performance analysis. Restore settings from task configuration or compared model configuration. Use the full Spec Kit workflow and parallel subagents.

## Restated

Training progress and the best model should be visible in ClearML during and after training. Configuration and diagnostic files should stay out of new task artifact inventories without losing replay capability.

## Origin & Context

- **Raised by**: repository user.
- **Trigger**: user-observed tracking and artifact concerns; request to revalidate after the next release before implementation.
- **Authorization**: user subsequently requested implementation of the approved plan.

## First-Glance Unknowns

- Which telemetry gaps remain after release v0.10.0?
- Which configuration/artifact requirements are already implemented?
- Which real execution modes can be verified without affecting shared workloads?
