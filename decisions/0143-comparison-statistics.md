# ADR-0143 · Test paired model differences over shared eligible classes

## Context

Predictions from the two models refer to the same images and ground truth boxes. Testing each class independently without multiple-testing correction can overstate the evidence of change.

## Decision

Compute candidate-minus-baseline deltas. Use an image-level paired bootstrap for precision and the recall interval, and exact paired McNemar for the recall p-value. Apply Benjamini–Hochberg to the class-level precision and recall hypotheses together within a split. Restrict paired tests and pooled counts to shared eligible classes.

## Consequences

The pooled result lies outside the class correction family. An undefined test yields an unavailable verdict. The workbook retains one-sided measurements and exclusion reasons, so a class missing from one model cannot inflate the pooled comparison.

## Evidence

- [Eligibility, family and pooled rows](../src/clearml_yolo/core/comparison/assemble.py)
- [Numerical tests](../src/clearml_yolo/adapters/evaluation/comparison.py)
- [Statistical cases](../tests/test_comparison_significance.py)
- [Pooled and per-class display](../tests/test_comparison_workbook.py)
- [Comparison method](../docs/commands/cy-compare.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#scoring-and-statistics)
