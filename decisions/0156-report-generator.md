# ADR-0156 · Keep report-generator presentation behind the reporting adapter

## Context

CY owns the model roles, training-count provenance, artifact contracts and scientific results. Report-generator supplies the workbook readers, builders and reversible annotation mechanics.

## Decision

Recover the original dashboard layout, load its metric table through report-generator, check it has per-model metrics, and partition unknown counts. Pass the prepared pair to the developer and business builders. CY supplies the role identities and attaches [workbook annotations](0154-workbook-identity.md) after rendering.

## Consequences

Supplying a statistical comparison workbook as a dashboard is rejected. A library revision or presentation change must preserve both workbook contracts. Rendering cannot independently choose the matching policy or recalculate the evaluation.

## Evidence

- [CY integration and builders](../src/clearml_yolo/adapters/reporting/reports.py)
- [OOXML integration](../src/clearml_yolo/adapters/reporting/workbook_identity.py)
- [Real builder contract cases](../tests/test_report_class_availability.py)
- [Paired report outputs](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#machine-readability)
