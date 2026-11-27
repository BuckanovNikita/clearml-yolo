# ADR-0136 · Use digital-metrics behind CY evaluation adapters

## Context

Matching and AP depend on details such as tie ordering. Reimplementing those algorithms in a reporting path could give a different result for the same prediction population.

## Decision

The evaluation adapter invokes digital-metrics for calibration, matching and fixed evaluation. It copies library results into CY-owned records and checks the reconstructed PR output. For [paired statistics](0143-comparison-statistics.md), the adapter supplies numerical tests while CY defines class eligibility, the correction family and pooled population.

## Consequences

Scoring can run without a path for dashboards. Writers consume the computed values. Updating the pinned dependency requires preserving the scientific and format contracts at this boundary.

## Evidence

- [Scoring boundary](../src/clearml_yolo/adapters/evaluation/scoring.py)
- [Paired statistics bridge](../src/clearml_yolo/adapters/evaluation/comparison.py)
- [Separation and value preservation](../tests/test_evaluation_separation.py)
- [Shared comparison cases](../tests/test_shared_comparison.py)
- [Evaluation reference](../DOCS.md#evaluation-and-metrics)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#shared-library)
