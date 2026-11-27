# ADR-0154 · Attach readable model identity while retaining original workbook bytes

## Context

People reading a workbook need a model name and role. Later runs reading the workbook need the original scientific keys, full identity and a way to detect edits.

## Decision

CY owns the model-identity and display-alias schemas. Use report-generator's OOXML packaging to attach readable footer lines, links and hidden identity metadata. Keep the original workbook recoverable. If both model identity and [readable class labels](0157-readable-class-labels.md) apply, wrap the presentation envelope inside the identity envelope.

## Consequences

Visible footers use names and roles and can link to ClearML. Reading a workbook with an intact annotation envelope checks its fingerprint and rejects edits after annotation. Re-annotation starts from the recovered original. Third-party software that strips custom metadata can remove this evidence.

## Evidence

- [Envelope and footer contract](../src/clearml_yolo/adapters/reporting/workbook_identity.py)
- [Identity round-trip cases](../tests/test_workbook_identity.py)
- [Workbook identity in user documentation](../docs/formats/workbooks.md)
- [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#identity-footer)
