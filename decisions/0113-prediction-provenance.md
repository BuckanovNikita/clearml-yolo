# ADR-0113 · Bind predictions to their bytes, checkpoint and naming mode

## Context

A CSV filename alone cannot establish which checkpoint produced it or how to join its image names to ground truth.

## Decision

Write a sibling `.provenance.json` identifying the prediction bytes, naming mode and available checkpoint/model identity. Validate the sidecar before consuming its identity or digest. Propagate the resulting model identity to evaluation outputs.

## Consequences

Replacing the CSV invalidates a bound digest. A missing sidecar on a historical CSV leaves only the canonical ground truth membership check for image identity and requires another source for model labeling. Recorded `stem` or `path` mode blocks evaluation even when the apparent names happen to match.

## Evidence

- [Sidecar writer and reader](../src/clearml_yolo/adapters/clearml/results.py)
- [Evaluation consumer](../src/clearml_yolo/application/use_cases/metrics.py)
- [Identity flow tests](../tests/test_identity_flows.py)
- [Noncanonical provenance cases](../tests/test_metrics.py)
- [Prediction format](../docs/formats/predictions.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#provenance-sidecar)
