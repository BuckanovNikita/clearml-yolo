# ADR-0131 · Fit confidence thresholds only on validation images

## Context

Optimizing the confidence cutoff on the test population would reuse test outcomes to choose the scoring rule.

## Decision

Require a `val` split and forbid logical image overlap between `val` and `test`. Match validation images, including background images, and select either one threshold per class or one global threshold repeated for every class. Freeze the resulting mapping for every requested split.

## Consequences

A request to score only `test` still requires validation data and writes `metrics_best_confidences_val.csv`. Saving 17 significant digits preserves the selected floats. Comparison can reuse these thresholds without fitting on its comparison split.

## Evidence

- [Split policy](../src/clearml_yolo/core/evaluation/policy.py)
- [Threshold optimization](../src/clearml_yolo/adapters/evaluation/scoring.py)
- [Frozen-threshold and precision tests](../tests/test_metrics.py)
- [Evaluation settings](../docs/configuration/evaluation.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#thresholds)
