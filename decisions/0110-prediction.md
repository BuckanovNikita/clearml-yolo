# ADR-0110 · Predict the selected ground truth images with one checkpoint

## Context

`cy-predict` serves raw prediction consumers and later evaluation. Grouping by split keeps the batch composition of a test prediction independent of the other requested splits.

## Decision

Resolve [ground truth](0102-ground-truth-source.md) and [weights](0111-weight-selection.md), run native inference for the unique images in each requested split, and combine the groups into a [prediction CSV](0112-prediction-csv.md) with [provenance](0113-prediction-provenance.md). Record each group using the [inference settings contract](0114-prediction-settings.md).

## Consequences

The CLI defaults to `predict.csv` under the run directory. Missing image results fail the prediction. A successful empty detection set still has a CSV header. The command guide's exit table lists FiftyOne errors under exit 1. The optional publisher catches backend setup and publication errors, logs a warning and lets prediction continue.

## Evidence

- [Command output routing](../src/clearml_yolo/entrypoints/hydra/common.py)
- [Prediction workflow](../src/clearml_yolo/application/use_cases/predict.py)
- [Optional publication handling](../src/clearml_yolo/application/use_cases/publication.py)
- [Workflow cases](../tests/test_predict.py)
- [Command guide and exit table](../docs/commands/cy-predict.md)
- [Triage for the FiftyOne exit-code discrepancy](https://linear.app/sip-ds-team/issue/SIP-346)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#inputs)
