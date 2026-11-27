# ADR-0100 · Convert a YOLO dataset into ground truth

## Context

The other CY commands consume pixel boxes and explicit image membership. A YOLO dataset supplies class indices, normalized boxes and files grouped by split.

## Decision

`cy-ground-truth` connects the dataset YAML to its owning task, reads the effective configuration and translates each detection into a row of the [ground truth CSV](0101-ground-truth-csv.md). Class names must agree under the installed Ultralytics reader and the historical YAML interpretation. Empty images receive membership rows.

## Consequences

When the test split is absent or empty, the seed and `test_fraction` select validation images by name for the test split. A reader disagreement fails before CSV output. Successful conversion registers the resulting CSV as `gt_csv`.

## Evidence

- [Conversion workflow](../src/clearml_yolo/application/use_cases/ground_truth.py)
- [YOLO reader and split selection](../src/clearml_yolo/adapters/yolo/ground_truth.py)
- [Conversion, YAML compatibility and split tests](../tests/test_ground_truth.py)
- [Command guide](../docs/commands/cy-ground-truth.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#yolo-conversion-with-cy-ground-truth)
