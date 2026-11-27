# ADR-0133 · Compute AP and precision–recall curves over the confidence ranking

## Context

A configured operating threshold or an optional prediction filter can remove detections needed to reconstruct the precision–recall curve.

## Decision

Use geometry-valid predictions from before optional preprocessing for AP and PR. Follow the library's confidence ordering and the selected AP integration method. Compare reconstructed per-class AP50 against the authoritative library result and fail on disagreement.

## Consequences

Fixed-threshold counts and AP describe different populations and can respond differently to a preprocessing change. A prediction-only class has unavailable recall. The report payload carries per-class PR and AP values for rendering.

## Evidence

- [PR reconstruction](../src/clearml_yolo/adapters/evaluation/pr_curves.py)
- [AP consistency check](../src/clearml_yolo/adapters/evaluation/scoring.py)
- [Arithmetic and unavailable-recall cases](../tests/test_pr_curves.py)
- [Evaluation configuration](../docs/configuration/evaluation.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#two-prediction-populations)
