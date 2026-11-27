# ADR-0321 · Publish scientific results as ClearML plots, tables and scalars

A reviewer needs to inspect split and model results in ClearML without first downloading every workbook.

**Decision.** Render tables and finite scalar values from the computed results. [Scoring evidence](0134-evaluation-lineage.md) supplies the observations. Confusion plots expose counts and normalized views, and test precision–recall curves use their recorded observations. Comparison publishes headline verdicts from eligible hypotheses. Plot slots are resolved using readable model identities.

**Consequences.** The candidate's comparison evidence can appear alongside evaluation results. Baseline evidence remains available in the artifacts. Missing headline inputs can suppress a scalar. SDK call tests cover series selection and values; confirming interactive rendering requires the actual UI.

[ClearML reporting adapter](../src/clearml_yolo/adapters/clearml/report.py) · [Plot and context selection](../src/clearml_yolo/adapters/clearml/results.py) · [Table and headline cases](../tests/test_clearml_report.py) · [Published views](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/a6a78e895cb84a2fc960d4b3f91e8327f2ea3e89)
