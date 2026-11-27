# ADR-0152 · Determine report eligibility separately for each model

## Context

A model may have few training examples for a class, or no trustworthy count. Filling an unknown count with zero would conflate missing evidence with a small measured population.

## Decision

Read a nonnegative integral count per class from the [original training population](0151-population-counts.md). The report builders use `min_train_count` to filter eligible rows. Partition missing or invalid count rows before invoking the builders and retain those rows with reasons.

## Consequences

Classes below the configured minimum appear in the excluded-class sheet. Unknown counts produce `Unknown training count` and `Report issues` sheets and a warning. Model-level aggregates use each model's own eligible classes. Paired differences use shared classes with the required values.

## Evidence

- [Training count contract](../src/clearml_yolo/core/report_counts.py)
- [Partition and issue annotations](../src/clearml_yolo/adapters/reporting/count_issues.py)
- [Count issue cases](../tests/test_report_count_issues.py)
- [One-sided availability cases](../tests/test_report_class_availability.py)
- [Eligibility and unavailable counts](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#training-counts-and-warnings)
