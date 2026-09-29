# Data Model

## Parameter inventory

Native template key → applicable stages (train, predict, neither), upstream comment/value,
project override or explicit prediction reference. Every installed template key is classified.

## Resolved settings

A complete stage mapping produced by configuration composition. Native options have no
fallback in execution helpers. Required keys must exist; optional null remains meaningful.
Model/source/project/name may be resolved by explicit command ownership.

## Execution record

Requested stage mapping after command-owned derivations, effective native args, and stride-normalized
predictor target size. Checkpoint training size is diagnostic and never selects inference size.
Prediction references are resolved in retained execution YAML, not in editable examples.

The normalized target is not per-batch tensor telemetry: rect=true can use smaller tensors.
