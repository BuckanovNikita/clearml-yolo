# ADR-0132 · Score detections at fixed operating thresholds

## Context

Changing preprocessing, assignment or threshold policy can change counts even with identical prediction bytes.

## Decision

Validate prediction membership before filtering. Optionally deduplicate ground truth, reject invalid prediction geometry from scoring, and optionally filter predictions by confidence or configured NMS. Match the prepared rows at the configured IoU and strategy, then apply the frozen class thresholds through the [digital-metrics integration](0136-digital-metrics.md).

## Consequences

TP, FP, FN and confusion results describe the configured operating point. Predictions of a class absent from ground truth can still contribute false positives. Source rows excluded by preprocessing stay traceable in the [audit output](0134-evaluation-lineage.md).

## Evidence

- [Preparation and scoring](../src/clearml_yolo/adapters/evaluation/scoring.py)
- [Split policy](../src/clearml_yolo/application/use_cases/metrics.py)
- [Invalid geometry tests](../tests/test_invalid_prediction_workflows.py)
- [Prediction-only classes](../tests/test_metrics.py)
- [Matching and preprocessing options](../docs/configuration/evaluation.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#two-prediction-populations)
