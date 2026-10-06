# Feature Specification: Native FiftyOne Evaluations

**Feature Branch**: `master`
**Created**: 2026-10-06
**Status**: Implemented and verified; released in v0.16.0
**Input**: Imported predictions must provide the native FiftyOne evaluation experience.

## User Scenarios & Testing

### User Story 1 — Browse exact evaluations (P1)

Reviewers open a published evaluation, inspect counts and confusion cells, and navigate
to the actual detections without changing the existing matching methodology.

**Independent test**: Publish known TP/FP/FN and wrong-class cases, reload, and inspect
the registered evaluation and its selected labels.

1. Given an evaluated split, publication exposes a named, reloadable evaluation.
2. Given wrong-class and duplicate detections, counts and confusion entries equal the
   existing project results; clicks select the corresponding labels.
3. Given an interrupted publication, retry repairs this task without changing other runs.

### User Story 2 — Inspect complete reports (P2)

Reviewers inspect the existing precision-recall curves and average precision values.

**Independent test**: Compare persisted reports and plots with producer outputs.

1. Existing AP50 curves and AP50/AP75/AP50–95 values retain their source values.
2. Missing historical data and subset AP evidence are explicitly unavailable.
3. Fixed-threshold subset reports restore full results after leaving the subset.

### Edge Cases

Empty images/splits, no ground truth for a class, no predictions, filtered predictions,
numeric/Unicode class names, duplicate/wrong-class associations, changed split membership,
fresh-process reload, native rename/delete, and publication retry.

## Requirements

- **FR-001**: Publish one native evaluation per task/split without rematching.
- **FR-002**: Preserve exact matches, counts, confusion entries and raw predictions.
- **FR-003**: Expose existing curves/AP with truthful labels and unavailable states.
- **FR-004**: Support persisted reload, filtering, exact click-through, rename and deletion.
- **FR-005**: Preserve other tasks and repair task-owned partial publications on retry.
- **FR-006**: Keep optional publication failure and disabled-import isolation contracts.
- **FR-007**: Extend receipts/run links with evaluation identities; preserve old payload reads.
- **FR-008**: Provide a separately installable UI extension without modifying FiftyOne.
- **FR-009**: Apply only to new publication/reruns; no automatic historical migration.

### Key Entities

Evaluation identity (task/split), immutable source report, evaluated label association,
saved result, and publication receipt.

## Success Criteria

- **SC-001**: All fixture counts and confusion cells match authoritative outputs exactly.
- **SC-002**: Saved reports and label navigation survive a fresh process.
- **SC-003**: Curves/AP preserve producer precision; unavailable values are never invented.
- **SC-004**: Retry and concurrent-task checks preserve unrelated evaluations.
- **SC-005**: Real database and App checks demonstrate browsing and reporting behavior.

## Assumptions

The user selected existing matches, full existing reports, a UI adapter for exact
wrong-class semantics, and new publications/reruns only. No new metric definitions,
additional IoU curves, mAR, dependency revision changes, or global plugin auto-install.
