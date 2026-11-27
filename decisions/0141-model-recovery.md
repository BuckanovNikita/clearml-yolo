# ADR-0141 · Recover checkpoints and frozen thresholds for comparison

## Context

A candidate or baseline may be a local checkpoint, a current ClearML task or a historical task with an older artifact layout.

## Decision

A local reference supplies weights and thresholds. For a ClearML reference, resolve an explicit task or select by project/name/tags. The automatic baseline is the latest eligible completed `prod` task excluding the current task. Model recovery first inspects the `clearml_yolo_checkpoint_role` metadata for `best`, then the best-checkpoint filename, then registration order with a warning. Ambiguity in the first two tiers fails.

## Consequences

CY can recover thresholds from a model or compatible historical artifacts and dashboards. An explicit threshold map takes precedence. The technical reference describes a `best` tag as the first selector. A model bearing only that tag does not satisfy the implemented metadata check. [Discrepancy under triage](https://linear.app/sip-ds-team/issue/SIP-352)

## Evidence

- [Model and threshold recovery](../src/clearml_yolo/adapters/clearml/models.py)
- [Model reference resolution](../src/clearml_yolo/application/use_cases/compare.py)
- [Recovery cases](../tests/test_comparison_recovery.py)
- [Technical reference](../DOCS.md#comparison)
- [Comparison configuration](../docs/commands/cy-compare.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#recovering-historical-models)
