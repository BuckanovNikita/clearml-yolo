# ADR-0134 · Retain a row-level explanation for each evaluation outcome

## Context

Filtering can change frame indices, so an index into a prepared table is insufficient to explain which original row was matched or discarded.

## Decision

Assign `source_row_id` and `object_id` before preprocessing. Carry source identities through preparation into match relationships. Record TP, FP, FN, background, filtered, excluded or not-evaluated status with applicable reasons.

## Consequences

Invalid geometry has an explicit disposition. A consumer can trace a match to its input rows even when other rows disappear during scoring. Duplicate or unknown source identities fail validation.

## Evidence

- [Stage-specific dataframe validation](0015-dataframe-validation.md)
- [Source IDs and row assembly](../src/clearml_yolo/core/evaluation/result_rows.py)
- [Source-to-prepared evaluation](../src/clearml_yolo/adapters/evaluation/scoring.py)
- [Payload and relationship tests](../tests/test_evaluation_payload.py)
- [Result format](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#result-rows)
