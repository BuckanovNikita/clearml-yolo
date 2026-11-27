# ADR-0151 · Recover class counts from the evaluated checkpoint's training population

## Context

Evaluation data may come from a different dataset or time period than the checkpoint's training data. Using its counts to determine report eligibility would change the population being described.

## Decision

Bind original class counts to the checkpoint. When recovering from ClearML, verify the training task and checkpoint association before reading the prepared ground truth artifact. Count foreground annotations by class and original split. Preserve unknown counts when ownership or source data cannot be established.

## Consequences

Evaluation and comparison workbooks can show a `Dataset counts` sheet for each model role. An unavailable count stays `NA`. The [report eligibility rule](0152-report-eligibility.md) uses this model-owned population when deciding which class rows enter aggregates.

## Evidence

- [Recovery and association check](../src/clearml_yolo/adapters/clearml/population.py)
- [Original annotation counting](../src/clearml_yolo/adapters/storage/population.py)
- [Count provenance tests](../tests/test_training_count_provenance.py)
- [Dataset counts workbook cases](../tests/test_population_count_workbooks.py)
- [Workbook format](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#training-counts-and-warnings)
