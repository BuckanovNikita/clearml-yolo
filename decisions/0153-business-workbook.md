# ADR-0153 · Present a fixed-column business comparison

## Context

The two report audiences use different levels of detail. A business reader needs comparable model, difference and verdict sheets with stable column order.

## Decision

Use the report-generator business builder's fixed layout. Include listed columns present in the dashboards and retain the training-count column even when unavailable. Compute candidate-minus-baseline differences, sum example counts and honor configured exclusions from means. Present computed cell values, a population note and the [model identity footer](0154-workbook-identity.md).

## Consequences

The workbook can be read without spreadsheet formula recalculation. One-sided values produce `NA` differences. Scientific columns outside the business layout stay available in the source dashboards or developer view. The owner page specifies column order, colors and legends.

## Evidence

- [CY business builder invocation](../src/clearml_yolo/adapters/reporting/reports.py)
- [Real business workbook cases](../tests/test_report_business_layout.py)
- [Business layout decision](https://linear.app/sip-ds-team/issue/SIP-242)
- [Workbook presentation](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#report-workbooks)
