# ADR-0103 · Prepare native training datasets from validated records

## Context

The detector backends accept different layouts. Training must keep the original class names and the same image population across these representations.

## Decision

Validate the [ground truth CSV](0101-ground-truth-csv.md) and image geometry, then copy source images to the selected native layout. YOLO supports NDJSON and flat YOLO. Other supported detector families use COCO. Quote class names in generated YAML to preserve values such as `1e3` across readers.

## Consequences

Invalid boxes are dropped with a count. An image may survive as background, but training requires valid training boxes and the required splits. NDJSON preserves basenames, while flat and COCO copies use numbered filenames. CY reuses this work through the [prepared dataset cache](0104-dataset-cache.md).

## Evidence

- [Record validation and filtering](../src/clearml_yolo/adapters/storage/dataset_records.py)
- [Native format writers](../src/clearml_yolo/adapters/storage/dataset_export.py)
- [Export contract cases](../tests/test_dataset_export.py)
- [COCO layout cases](../tests/test_coco_dataset.py)
- [Dataset formats](../docs/formats/datasets.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#training-validation-and-preparation)
