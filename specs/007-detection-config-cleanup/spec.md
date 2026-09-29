# Feature Specification: Detection configuration cleanup

**Feature Branch**: `007-detection-config-cleanup`
**Created**: 2026-09-29
**Status**: Approved for implementation
**Input**: Configuration cleanup, task-derived outputs, and split parity.

## User Scenarios & Testing

### User Story 1 - Edit focused detection examples (Priority: P1)

An operator configures training and prediction independently, with relevant editable
settings first and upstream documentation retained.

**Independent Test**: Generate examples, compose every command and override devices.
**Acceptance Scenarios**:

1. Given generated examples, training device is null and prediction device is [-1].
2. Given a training device override, prediction retains its own default or override.
3. Given examples, controlled settings are commented; runtime records contain actual values.

### User Story 2 - Find outputs by tracking identity (Priority: P1)

An operator finds an invocation's outputs under its active project, task name and task ID.

**Independent Test**: Use distinct task IDs and unsafe names, then verify paths and overrides.
**Acceptance Scenarios**:

1. Implicit roots are runs/<safe-project>/<safe-task>-<task-id>/ with existing stage layout.
2. Explicit roots/run IDs retain precedence and conflicting stage routes still fail.
3. Renamed or remotely owned task identity determines the implicit root, not requested names.

### User Story 3 - Compare complete split evaluations (Priority: P1)

An evaluator receives the same evidence for train, val and test, with one calibration.

**Independent Test**: Evaluate three disjoint splits and inspect uploads and publication.
**Acceptance Scenarios**:

1. Default evaluation produces exactly 13 successful metric artifacts per split, with
   identical normalized kinds, separate names/paths and identical frozen thresholds.
2. Explicit subsets remain supported; missing splits and unsupported empty inputs fail.
3. Enabled pipeline publication has one owner receipt containing all selected evaluation
   payloads; cy-val has no publication. Zero predictions retain all required evidence.

### Edge Cases

Unsafe/empty/reserved path components, duplicate split selections, missing val calibration,
missing plot files, upload rejection, empty predictions, explicit null device, renamed tasks,
explicit standalone model/data overrides, and skipped pipeline stages.

## Requirements

### Functional Requirements

- **FR-001**: Prediction device defaults independently to [-1]; training remains null.
- **FR-002**: Examples put active settings before commented controlled/inapplicable settings,
  preserving upstream comments/order within sections. Comment task, mode, data, project,
  name in both groups and source/model in prediction; training model/classes/fraction stay editable.
- **FR-003**: Composition and supported standalone overrides remain complete; runtime YAML
  retains actual derived settings and native callbacks remain disabled under cy tracking.
- **FR-004**: Implicit outputs use active task identity and safe single path components.
  Explicit output/run ID precedence, isolation and producer-consumer routing are preserved.
- **FR-005**: cy, cy-val and cy-metrics default to train/val/test including direct calls.
  Calibrate only on val once and reuse frozen thresholds for every selected split.
- **FR-006**: A centralized inventory requires 13 metric artifacts per split: two dashboards,
  two matching tables, confusion matrix, summary, raw metrics, thresholds, four CI plots,
  and evaluation JSON. Missing outputs/uploads fail.
- **FR-007**: Preserve schema-version-1 exact evaluation payloads and MetricsResult.evaluations;
  publication consumes existing matching without rematching or FiftyOne evaluation.
- **FR-008**: Preserve default publication eligibility (cy, cy-predict, cy-metrics only),
  one owner receipt, disabled nested publication, GT identity, resolved media and task namespaces.
- **FR-009**: Comparison/reports stay test-only; shared inputs, methodology, receipts and
  comparison/report artifacts are outside split parity. Preserve explicit subsets and errors.
- **FR-010**: Update guidance and Russian README, preserve dependencies and feature 006,
  verify repository gates and real isolated three-split execution with downloaded evidence.

### Key Entities

Task identity (project/name/ID), output root, selected splits, frozen threshold map,
per-split artifact inventory, exact evaluation payload, invocation publication receipt.

## Success Criteria

- **SC-001**: All generated commands compose and independent device overrides survive.
- **SC-002**: Distinct task IDs yield distinct roots; unsafe names cannot escape their root.
- **SC-003**: Three-split evaluation yields 39 successful split artifacts with equal kinds.
- **SC-004**: Publication reuses dataset identity across roots and emits one valid receipt.

## Assumptions and Clarifications

The supplied plan resolves scope and policy; no material user clarification remains.
Explicit output settings retain their existing semantics. No dependency changes, commit,
push, shared-service restart or deployment are included. Existing feature 006 is the base.
