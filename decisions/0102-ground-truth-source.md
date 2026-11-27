# ADR-0102 · Resolve a ground truth source once per invocation

## Context

A stage can receive local annotations or a versioned ClearML Dataset. Composed commands need the same selection and a stable interpretation of relative image paths.

## Decision

Accept a local CSV, a dataset ID, or a project/name selector with optional version. Resolve the selector once and pass the resolved record into nested stages. A ClearML dataset must be finalized and contain exactly root `dataset.csv`. Download it without soft links, and record the resolved dataset identity, version and CSV digest.

## Consequences

Local paths emit a warning. An unversioned project/name lookup can select a newer version on a later invocation. The linked SDK tests simulate ClearML. A live dataset download requires separate evidence. The executable selector and the evidence of what CY actually read serve different purposes.

## Evidence

- [Source resolution](../src/clearml_yolo/application/ground_truth.py)
- [ClearML dataset adapter](../src/clearml_yolo/adapters/clearml/datasets.py)
- [Source resolution tests](../tests/test_ground_truth_sources.py)
- [Source forms](../docs/formats/ground-truth.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#ground-truth-sources)
