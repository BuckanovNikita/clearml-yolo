# ADR-0101 · Preserve image membership and lexical identity in ground truth

## Context

A background image contributes an evaluation opportunity even when it has no object boxes. Names that look numeric can identify distinct images or classes.

## Decision

Use a detection CSV with `image_name`, `image_path`, `instance_label`, four pixel corner coordinates and `split`. An empty class and empty coordinates represent a background image. The reader preserves lexical identity and resolves relative image paths against the CSV directory.

## Consequences

Preparation verifies the mapping of image names to files and splits. Duplicate background rows and duplicate valid annotations are errors. Each invalid box is dropped and counted separately, even if an identical invalid row appears twice. The literal reserved class `background` is rejected before opening media. Consumers validate what they use. Prediction selects images and does not validate the class vocabulary.

## Evidence

- [Stage-specific dataframe validation](0015-dataframe-validation.md)
- [Detection CSV reader](../src/clearml_yolo/adapters/storage/file_io.py)
- [Preparation validation](../src/clearml_yolo/adapters/storage/dataset_records.py)
- [CSV contract cases](../tests/test_dataset_records.py)
- [Reserved label decision](https://linear.app/sip-ds-team/issue/SIP-218)
- [Ground truth format](../docs/formats/ground-truth.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#csv-interpretation)
