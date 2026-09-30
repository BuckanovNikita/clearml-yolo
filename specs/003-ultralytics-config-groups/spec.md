# Feature Specification: Native Ultralytics configuration groups

**Feature Directory**: `specs/003-ultralytics-config-groups`

**Created**: 2026-09-28

**Status**: Implemented; original acceptance is recorded in
[historical verification](verification-2026-09-28.md). Current amendments and their
verification scope are described below.

**Input**: Replace sparse stage settings and raw-file loading with a full native training
configuration, prediction overrides, preserved upstream comments, and replayable local YAML.

## Current contract evidence

The 2026-09-28 record verifies the original native-YAML artifact/replay behavior; it does
not verify the amended no-configuration-artifact requirement. Later
[resolved-configuration evidence](../009-resolved-config-uploads/verification-2026-09-30.md)
and [native-tracking evidence](../010-native-clearml-integration/verification.md) record
canonical configuration publication, consolidated performance artifacts and owner callbacks.
Direct native replay belongs to the original record; remote cloned-task recovery remains
mocked, not a live remote-agent result. The
[documentation audit](../../docs/evidence/2026-09-30-instruction-contract-audit.md)
records current static/configuration checks without repeating native execution.

## User Scenarios & Testing

### User Story 1 - Paste native configuration (Priority: P1)

An experiment author initializes examples, pastes upstream YAML into the shared group,
and changes native settings using the same top-level Hydra paths for every model command.

**Why this priority**: Removes translation between native and wrapper configuration.

**Independent Test**: Generate examples and compose all commands without model execution.

**Acceptance Scenarios**:

1. **Given** a fresh directory, **When** initialization runs, **Then** eight command examples
   and two native group files are created without ClearML tasks or model-runtime imports.
2. **Given** unchanged upstream YAML in `ultralytics/default.yaml`, **When** a command is
   composed with `ultralytics.epochs=10`, **Then** the supplied setting resolves without `+`.
3. **Given** an old nested mapping or non-null `cfg`, **When** invoked, **Then** execution
   fails with migration guidance before training or prediction.

### User Story 2 - Override prediction settings (Priority: P1)

An author shares model settings and overrides only prediction-specific values.

**Why this priority**: Training and inference need consistent shared settings with explicit exceptions.

**Independent Test**: Capture native training and prediction arguments with isolated substitutes.

**Acceptance Scenarios**:

1. **Given** shared image size and a prediction batch override, **When** prediction runs,
   **Then** it inherits image size and uses its explicit batch override.
2. **Given** an explicit prediction null or native default value, **When** shared settings
   differ, **Then** the explicit prediction value wins, including over shared CLI overrides.
3. **Given** a trained pipeline checkpoint, **When** prediction runs, **Then** it uses that
   checkpoint and the pipeline's image selection and output routing.

### User Story 3 - Inspect and replay native settings (Priority: P2)

An author obtains commented, resolved native YAML locally and replays an individual stage
using native Ultralytics and retained source manifests.

**Why this priority**: Reproducibility requires actual execution inputs rather than wrapper options.

**Independent Test**: Parse exported YAML and verify that ClearML stores canonical run
configuration without a native-YAML artifact.
Direct native replay remains a separately authorized integration check. The
[2026-09-28 record](verification-2026-09-28.md) is historical direct-replay evidence;
current configuration-only publication evidence and limitations are listed above.

**Acceptance Scenarios**:

1. **Given** stage execution, **When** settings are exported, **Then** original upstream
   comments remain, irrelevant settings are commented, and active values match native inputs.
2. **Given** multiple splits or comparison roles, **When** prediction completes, **Then** each
   distinct input has resolved YAML and a retained manifest supporting replay.
3. **Given** failed required performance publication or flush, **When** finalizing, **Then**
   the command and task fail while local YAML and other outputs remain.

### Edge Cases

- An upstream key not classified for stage applicability fails the coverage check.
- Training AutoBatch cannot silently become a prediction batch; require a valid override.
- Explicit conflicting prediction model or native pipeline output settings fail.
- Explicit native nulls remain distinct from absent overrides; unknown keys fail validation.
- Existing files, symlinks, parent collisions and paths with spaces retain generator safeguards.
- Comments and values must not leak credentials. Raw source dataset images are never uploaded
  as artifacts; owner-only native training/validation previews remain permitted.

## Requirements

### Functional Requirements

- **FR-001**: Initialization MUST generate eight command files and native group files under
  `ultralytics/default.yaml` and `ultralytics_predict/default.yaml`.
- **FR-002**: The shared group MUST cover the installed upstream default configuration and
  retain its license header, ordering and comments; unchanged upstream YAML MUST be accepted.
- **FR-003**: `cy`, `cy-train`, `cy-predict`, `cy-val` and `cy-compare` MUST expose top-level
  shared and prediction groups with ordinary Hydra overrides for supported native keys.
- **FR-004**: Prediction MUST inherit applicable shared values and then apply explicit
  prediction overrides, preserving explicit nulls and defaults; default confidence is 0.001.
- **FR-005**: Stage-irrelevant settings MUST be excluded from native execution and commented
  in effective YAML; training's internal validation settings MUST remain applicable.
- **FR-006**: The pipeline MUST own checkpoint, images, mode and output routing; comparison
  MUST use identical prediction settings for baseline and candidate.
- **FR-007**: Wrapper `cfg`, non-null native `cfg`, nested stage mappings and duplicate native
  comparison inference settings MUST fail with migration guidance.
- **FR-008**: Execution MUST save effective `ultralytics.yaml` or `ultralytics_predict.yaml`
  as applicable, plus split/role variants with actual inputs and retained prediction manifests.
- **FR-009**: Exported native YAML MUST contain no Hydra metadata or unresolved interpolation,
  and MUST be usable directly by native Ultralytics with the corresponding local inputs.
- **FR-010**: Effective/requested native YAML and prediction manifests MUST remain local.
  Canonical sanitized run Configuration Objects and native General parameters MUST support
  remote replay without configuration artifacts. Credentials and raw source dataset artifacts
  MUST NOT leak; owner-only native training/validation previews remain permitted.
- **FR-011**: Initialization MUST preserve collision protection and avoid importing model
  runtimes or creating ClearML tasks; one execution MUST retain one task and failure semantics.
- **FR-012**: Existing dependency pins MUST remain unchanged; heavy tests MUST wait for explicit
  user instruction. Focused lightweight tests and static checks may run now.

### Key Entities

- **Native template**: installed upstream parameter values, comments, order and applicability.
- **Shared configuration**: full native settings composed through Hydra.
- **Prediction overrides**: sparse explicit values layered over applicable shared settings.
- **Effective stage configuration**: resolved, stage-filtered values with owned execution inputs.
- **Replay record**: effective YAML, retained source manifest, and local/ClearML identity.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All five model commands compose generated examples and ordinary native overrides.
- **SC-002**: Every upstream key and original comment is accounted for in exported templates;
  every key has explicit stage classification.
- **SC-003**: Captured native invocation arguments match exported active YAML values, including
  split/role sources and checkpoint selection.
- **SC-004**: Removed interfaces reject use, collision scenarios preserve user files, and
  required artifact failures produce nonzero execution outcomes.
- **SC-005**: Separately authorized direct replay from local native YAML and ClearML replay from
  canonical configuration MUST verify real execution without configuration artifacts. Use the
  current contract evidence above; historical native-YAML artifact downloads do not establish
  the amended publication requirement, and mocked replay does not prove live remote recovery.

## Assumptions

- Defaults follow the installed locked Ultralytics package, not a vendored independent copy.
- `cy-val` retains prediction followed by calibration/evaluation rather than native `model.val()`.
- Heavy testing was explicitly authorized on 2026-09-28; its results and limits are dated evidence.
  Publishing a release is outside scope.

## Clarifications

### Session 2026-09-28

The approved plan supplies these decisions; no additional questions were necessary:

- Native group files use native keys at their root; command defaults package them under the groups.
- The prediction file activates `conf: 0.001` and documents other keys as comments; composed
  prediction settings expose inherited keys for ordinary Hydra overrides.
- All five model commands share this configuration contract, including comparison and validation.
- Effective outputs include per-split/per-role YAML and persistent local image manifests.
- The initial restriction deferred heavy testing; the later instruction “you can run heavy tests” authorized it on 2026-09-28.
