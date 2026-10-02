# Feature Specification: Detection configuration cleanup

**Feature Branch**: `007-detection-config-cleanup`
**Created**: 2026-09-29
**Status**: Original feature implemented and verified in
[historical evidence](../../docs/evidence/2026-09-29-detection-config-cleanup.md);
current amendments and their verification scope follow.
**Input**: Configuration cleanup, task-derived outputs, and split parity.

## Current contract evidence

The 2026-09-29 record verifies the original 13-artifact-per-split inventory and test-only
comparison/report expectations. It does not establish the rewritten consolidated inventory
or standalone split override. Later
[dataset publication evidence](../../docs/evidence/2026-09-29-dataset-clearml-tracking.md),
[resolved-configuration evidence](../009-resolved-config-uploads/verification-2026-09-30.md)
and [native-tracking evidence](../010-native-clearml-integration/verification.md) record
consolidated performance publication, canonical configurations, owner callbacks and paired
current-test reports. Manifest-selected report behavior and standalone non-test composition
are checked statically in the
[documentation audit](../../docs/evidence/2026-09-30-instruction-contract-audit.md);
standalone non-test comparison/report execution was not exercised live by that audit.

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

1. Default evaluation produces one consolidated workbook per selected split and one exact
   validation-threshold CSV, with identical frozen thresholds represented in every workbook.
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
  retains actual derived settings. Installed native callbacks are enabled for the invocation
  owner and disabled for workers.
- **FR-004**: Implicit outputs use active task identity and safe single path components.
  Explicit output/run ID precedence, isolation and producer-consumer routing are preserved.
- **FR-005**: cy, cy-val and cy-metrics default to train/val/test including direct calls.
  Calibrate only on val once and reuse frozen thresholds for every selected split.
- **FR-006**: Publication MUST contain one consolidated evaluation workbook per selected split
  and one full-precision validation-threshold CSV per calibrated model. Component dashboards,
  matching tables, confusion output, raw metrics, plots and evaluation JSON MUST remain local;
  missing workbook inputs or required uploads fail.
- **FR-007**: Preserve schema-version-1 exact evaluation payloads and MetricsResult.evaluations;
  publication consumes existing matching without rematching or FiftyOne evaluation.
- **FR-008**: Preserve default publication eligibility (cy, cy-predict, cy-metrics only),
  one owner receipt, disabled nested publication, GT identity, resolved media and task namespaces.
- **FR-009**: Standalone comparison accepts a split override defaulting to test; pipeline
  comparison is fixed to test; reports follow the paired split in the comparison manifest.
  Thresholds always come from the current validation CSV or exact supplied values and are never
  calibrated on the compared split.
- **FR-010**: Update guidance and Russian README, preserve dependencies and feature 006,
  verify repository gates and real isolated three-split execution with downloaded evidence.

### Key Entities

Task identity (project/name/ID), output root, selected splits, frozen threshold map,
per-split artifact inventory, exact evaluation payload, invocation publication receipt.

## Success Criteria

- **SC-001**: All generated commands compose and independent device overrides survive.
- **SC-002**: Distinct task IDs yield distinct roots; unsafe names cannot escape their root.
- **SC-003**: Three-split evaluation yields three consolidated evaluation workbooks and one
  exact validation-threshold CSV, with required local diagnostics retained.
- **SC-004**: Publication reuses dataset identity across roots and emits one valid receipt.

## Assumptions and Clarifications

The supplied plan resolves scope and policy; no material user clarification remains.
Explicit output settings retain their existing semantics. No dependency changes, commit,
push, shared-service restart or deployment are included. Existing feature 006 is the base.
