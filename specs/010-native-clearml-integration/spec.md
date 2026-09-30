# Feature Specification: Native ClearML tracking

**Feature Branch**: `010-native-clearml-integration`
**Created**: 2026-09-30
**Status**: Approved for implementation
**Input**: User-approved native tracking, best-model publication and performance-only artifact plan, revalidated against v0.10.0.

## Clarifications

### Session 2026-09-30

The approved conversation supplies these decisions; no additional questions were required.

- Progress means native epoch reporting; custom batch scalars are excluded.
- New tasks must contain only performance data artifacts and one native best Output Model. Historical tasks remain unchanged.
- Settings are recovered from current-task configuration or the compared model's source-task configuration.
- Frozen validation thresholds remain performance data; comparison uses identical current-test images and shared inference settings.
- Existing dependencies and feature 009 configuration-resolution behavior remain intact. Commit, push and release are excluded.

## User Scenarios & Testing

### User Story 1 - Inspect training while it runs (Priority: P1)

A training operator sees native loss and progress while training continues, including distributed training.

**Why this priority**: final-only events cannot support monitoring a running experiment.

**Independent Test**: hold a multi-epoch training operation open after a completed epoch and observe its native telemetry before allowing completion.

**Acceptance Scenarios**:

1. **Given** a multi-epoch native training run, **When** an epoch completes, **Then** its native training loss and available validation/learning-rate/time values are reported before the run finishes.
2. **Given** distributed training, **When** rank-zero epoch events become available, **Then** the owner reports them once in their original order without creating worker tasks.
3. **Given** explicit disabled plotting, **When** training runs, **Then** no plots are forced while native scalar reporting remains enabled.
4. **Given** callback, journal or interruption failure, **When** finalization is attempted, **Then** the command and task fail and local diagnostics remain available.

### User Story 2 - Retrieve the native best model (Priority: P1)

An operator retrieves the best checkpoint from the successful training task and uses it for subsequent evaluation.

**Why this priority**: experiment completion is meaningful only when its actual best model is available.

**Independent Test**: download the successful task's single native best Output Model, compare its bytes with the local checkpoint and load it.

**Acceptance Scenarios**:

1. **Given** successful training, **When** the task completes, **Then** exactly one native best Output Model has verified uploaded bytes and no duplicate weight artifact.
2. **Given** missing weights, incorrect downloaded bytes or failed upload/flush, **When** the task finalizes, **Then** successful completion is prevented.
3. **Given** an incomplete distributed journal, **When** completion is attempted, **Then** no final native model publication callback is executed.

### User Story 3 - Analyze clean artifacts and replay configuration (Priority: P2)

An operator finds only model-performance evidence in artifacts and restores execution settings from task configuration, including compared models' source tasks.

**Why this priority**: configuration clutter obscures useful evidence and must not become a second replay source.

**Independent Test**: inspect every command's publication inventory and replay using configurations without any configuration artifact.

**Acceptance Scenarios**:

1. **Given** an execution invocation consuming YAML/JSON inputs, **When** publication completes, **Then** temporary numbered YAML, train_data_overrides.json, manifests and receipts are absent from artifacts.
2. **Given** a replayed task, **When** original input paths are unavailable, **Then** canonical task configuration supplies the required settings with existing resolution and sanitization behavior.
3. **Given** compared models with source-task provenance, **When** comparison runs, **Then** the compared model links to its source-task configuration for provenance and recovery; current shared comparison inference settings remain authoritative and are not replaced by source training arguments.
4. **Given** validation-calibrated thresholds, **When** test comparison runs, **Then** both models use the frozen source thresholds on identical current-test images; thresholds are not recalibrated on test.
5. **Given** missing required source configuration, **When** recovery is requested, **Then** an actionable failure identifies the missing configuration rather than silently inventing values.

### Edge Cases

- Incomplete trailing journal records are not reported until complete; corruption or an incomplete final journal fails completion.
- Earlier telemetry may exist on failed runs; it does not authorize successful task completion or final model publication.
- Native final-best validation values retain upstream epoch semantics; equality of epoch indices does not imply duplicate relay events.
- Identical CSV contents publish once; logical aliases remain satisfied.
- Remote overrides, explicit nulls, comments and credential sanitization retain existing configuration-resolution semantics.
- Historical weight and threshold readers remain supported; no historical configuration artifacts become required.

## Requirements

### Functional Requirements

- **FR-001**: Training MUST report installed native epoch losses, available learning rates, validation metrics and epoch time during execution, including DDP, preserving native names and epoch indices.
- **FR-002**: Each invocation MUST own one tracking task; only its owner may report, upload or run native publication callbacks. Nested stages reuse that task.
- **FR-003**: Distributed events MUST be dispatched once, in order, with partial records retained until complete; final native publication MUST wait for a complete validated journal.
- **FR-004**: Callback, journal, computation, upload, flush and interruption failures MUST fail command/task, stop owned relay activity and preserve local outputs.
- **FR-005**: Successful training MUST expose exactly one verified native best Output Model matching the local checkpoint, without a duplicate weight artifact.
- **FR-006**: Native plots and debug samples MUST remain available according to installed callback behavior and explicit plot settings; scalars MUST remain enabled when plots are disabled.
- **FR-007**: New task artifacts MUST contain only canonical ground-truth/prediction CSVs, frozen validation-threshold CSVs, evaluation/comparison workbooks and final performance reports; identical tables MUST be deduplicated.
- **FR-008**: Execution settings, dataset overrides, normalization, source references and meaningful provenance MUST use sanitized Configuration Objects or native General parameters; temporary files, manifests and diagnostic receipts MUST remain local.
- **FR-009**: Current-task replay and compared-model recovery MUST use canonical task/source-task configuration without configuration artifacts, preserve feature 009 resolution behavior and fail actionably for missing required configuration.
- **FR-010**: Comparison MUST retain frozen source validation thresholds, identical paired current-test inputs and shared comparison inference settings; historical weight/threshold compatibility MUST remain intact.
- **FR-011**: Historical tasks, external dependency revisions and unrelated workspace changes MUST remain unchanged.

### Key Entities

- **Invocation owner**: task identity and process authorized to publish.
- **Native event**: ordered epoch/callback observation with enough captured state for native reporting.
- **Best Output Model**: one native model identity linked to the verified local best checkpoint.
- **Performance artifact**: durable result evidence from the command-specific permitted inventory.
- **Replay configuration**: sanitized canonical settings linked to current or source training task.
- **Frozen threshold table**: validation-calibrated exact thresholds reused for test.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In every available multi-epoch acceptance mode, at least one completed epoch's loss is visible before training finishes.
- **SC-002**: A successful training task exposes exactly one downloadable, loadable best model whose bytes equal the local best checkpoint; failed publication never yields successful completion.
- **SC-003**: Every new acceptance task has zero configuration/diagnostic artifacts and only its approved performance inventory.
- **SC-004**: Replay and paired model comparison recover required settings without configuration artifacts and retain exact frozen validation thresholds.
- **SC-005**: Failed/interrupted acceptance scenarios leave no task-owned relay process/thread running; physical DDP unavailable for acceptance is explicitly reported as unverified.

## Assumptions

Installed native callback behavior defines metric series and epoch numbering. No custom batch telemetry, new CLI options, historical deletion, commit, push or release is included. Real execution and mocked tests are reported separately.
