# ADR-0130 · Evaluate saved predictions at frozen thresholds

## Context

Operators can evaluate a [prediction CSV](0112-prediction-csv.md) without rerunning the detector. Every score must identify its data, model and evaluation population.

## Decision

`cy-metrics` resolves [ground truth](0102-ground-truth-source.md) and [prediction provenance](0113-prediction-provenance.md), validates image membership, assigns source-row identities and [calibrates on validation](0131-calibration.md). It applies [fixed-threshold scoring](0132-fixed-scoring.md) and computes [precision–recall curves](0133-average-precision.md) for each requested split.

## Consequences

Each concrete split yields [audit rows](0134-evaluation-lineage.md), [dashboards and workbooks](0135-evaluation-outputs.md). Computation or a required output failure fails the standalone command. Optional visualization can warn and continue.

## Evidence

- [Metrics workflow](../src/clearml_yolo/application/use_cases/metrics.py)
- [Split evaluation](../src/clearml_yolo/application/evaluation.py)
- [Metrics workflow cases](../tests/test_metrics.py)
- [Metrics command](../docs/commands/cy-metrics.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#order-of-work)
