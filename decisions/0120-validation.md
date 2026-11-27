# ADR-0120 · Validate a checkpoint in one experiment task

## Context

A user with an existing checkpoint needs the same prediction and scoring contracts that the full pipeline applies, without running training.

## Decision

`cy-val` resolves the [ground truth](0102-ground-truth-source.md), invokes [prediction](0110-prediction.md) on the union of `val` and the requested splits, then runs [metrics](0130-metrics.md) on the requested splits with [validation-only calibration](0131-calibration.md). Both nested stages share the invocation's task and disable optional FiftyOne publication.

## Consequences

A test-only request still needs validation images and predictions to fit thresholds. The command writes `predictions.csv` under its output directory and evaluation products in its `metrics` subdirectory.

## Evidence

- [Validation orchestration](../src/clearml_yolo/application/use_cases/val.py)
- [Workflow composition cases](../tests/test_workflow_quality.py)
- [Publication behavior](../tests/test_publication_commands.py)
- [Validation command](../docs/commands/cy-val.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#validation-cy-val)
