# ADR-0140 · Compare candidate and baseline on a common split

## Context

A model comparison needs the same requested inference protocol, split membership and statistical rules for both models.

## Decision

`cy-compare` [resolves each model](0141-model-recovery.md), [re-infers or reuses its predictions](0142-comparison-inference.md) and applies its own frozen thresholds. It writes per-model dashboards and [paired statistics](0143-comparison-statistics.md) with a [manifest](0144-comparison-manifest.md). Only absence of the automatic baseline permits the [candidate-only result](0145-candidate-only.md).

## Consequences

A default-valued candidate is rejected. The evaluation settings guide says the comparison ignores `evaluation.backend`. The command's preflight and comparison implementation require a null backend and reject any other value. [Discrepancy under triage](https://linear.app/sip-ds-team/issue/SIP-347)

## Evidence

- [Comparison workflow and backend validation](../src/clearml_yolo/application/use_cases/compare.py)
- [Command preflight](../src/clearml_yolo/entrypoints/hydra/validation.py)
- [Comparison workflow cases](../tests/test_comparison_reinfer.py)
- [Candidate validation decision](https://linear.app/sip-ds-team/issue/SIP-211)
- [Comparison command](../docs/commands/cy-compare.md)
- [Evaluation settings guide](../docs/configuration/evaluation.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#model-references)
