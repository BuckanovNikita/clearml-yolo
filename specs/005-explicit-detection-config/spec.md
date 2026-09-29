# Feature Specification: Explicit Detection Configuration

**Created**: 2026-09-29
**Status**: Accepted for implementation
**Input**: Approved phase 005 plan and explicit implementation request.

## Clarifications

### Session 2026-09-29

- Shared prediction values use visible references to the training section.
- Project defaults explicitly enable compile and NMS; these are intentional departures from upstream defaults.
- Prediction confidence remains explicitly 0.001 for downstream calibration.
- Requested default image size is 960 (corrected by the user from a typo), without wrapper rounding.
- Use Spec Kit, preserving phase 004 and external dependency revisions.

## User Scenarios & Testing

### User Story 1 - Inspect useful detection parameters (Priority: P1)

An operator generates editable examples and can see every applicable detection setting,
its documentation, and any relationship with training settings.

**Independent Test**: Generate and load examples; compare active keys with the reviewed
parameter applicability inventory.

**Acceptance Scenarios**:

1. Given upstream configuration, generated training and prediction examples retain its
   documentation and comment out parameters irrelevant to detection in that stage.
2. Given an untouched prediction example, all applicable parameters are visible and active,
   with explicit shared references or stage-specific values.

### User Story 2 - Execute the configuration shown (Priority: P1)

An operator changes a native setting and receives the same value at the appropriate native
execution boundary without hidden helper defaults or cross-stage merging.

**Independent Test**: Capture native train and prediction arguments for all model commands.

**Acceptance Scenarios**:

1. Changing a referenced training value changes prediction; a prediction override wins.
2. Explicit false and supported null values survive; incomplete execution mappings fail.
3. Prediction, validation and paired comparison receive the same resolved inference values.

### User Story 3 - Explain effective behavior (Priority: P2)

An operator can distinguish configured values, command-owned inputs and native normalization
in retained local and ClearML records.

**Independent Test**: Real training and prediction produce usable artifacts with requested
and effective settings, including image-size normalization.

**Acceptance Scenarios**:

1. Configured image size 906 remains recorded even if native stride alignment changes the
   executed shape; checkpoint training size remains diagnostic, never an implicit default.
2. Pipeline-owned checkpoints, source membership and outputs remain isolated and inspectable.

### Edge Cases

Unknown native keys fail classification. Unsupported task/stage combinations cannot silently
produce a non-detection workflow. Null image size and absent training model fail instead of
selecting hidden values. Explicit weights conflict with a different prediction model.
Native optional null/auto behavior remains native. CSV ownership, source privacy, task failure,
upload/flush handling, fresh output routing and paired test membership remain unchanged.

## Requirements

### Functional Requirements

- **FR-001**: Classify every locked native parameter by detection train/predict applicability,
  including training validation; comment irrelevant keys and omit them from calls.
- **FR-002**: Populate prediction examples completely, preserving upstream documentation,
  with visible references for shared values and explicit prediction-specific values.
- **FR-003**: Define application defaults only in configuration: imgsz=960, compile=true,
  nms=true, training model=yolo11n.pt; prediction conf=0.001, batch=1, rect=true, save=false.
- **FR-004**: Resolve configured references before execution; prediction reads its own
  resolved section without an implicit merge with training settings.
- **FR-005**: Remove native helper/model fallbacks; preserve explicit supported values and
  reject incomplete or invalid resolved mappings with actionable configuration guidance.
- **FR-006**: Apply the same ownership rules to train, predict, val, pipeline and compare;
  keep candidate/baseline settings identical and existing command-owned inputs authoritative.
- **FR-007**: Retain requested and effective values separately, including native image-size
  normalization. Do not infer requested image size from checkpoints.
- **FR-008**: Document migration by regenerating old sparse examples; preserve CLI group names,
  native comments, existing dataset/output/tracking contracts and pinned dependencies.

### Key Entities

- Parameter classification: native name, applicable detection stages, evidence and default.
- Configured stage settings: resolved user choices, distinct from command-owned inputs.
- Execution record: requested settings and actual native arguments/shape after normalization.

## Success Criteria

- **SC-001**: Every native template parameter has a reviewed classification; no irrelevant
  parameter appears active in the corresponding generated example.
- **SC-002**: All five model commands pass configured values without application fallback;
  shared references and overrides produce the same result in built-in and exported examples.
- **SC-003**: Real training and inference retain usable outputs and inspectable configuration
  records; paired comparison uses identical settings and current-test membership.

## Assumptions

Detection is the supported task. Native internal automatic behavior is permitted when explicitly
selected through null/auto. Command-owned data/model/output derivations are documented exceptions
to native parameter ownership. Native runtime and dependencies stay pinned. No commit or push.
