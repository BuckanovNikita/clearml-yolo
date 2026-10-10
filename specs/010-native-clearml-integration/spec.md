# Feature Specification: Native ClearML tracking

**Feature Branch**: `010-native-clearml-integration`
**Created**: 2026-09-30
**Status**: Implemented, verified and converged; see [verification.md](verification.md)
**Input**: User-approved native tracking, best-model publication and performance-only artifact plan, revalidated against v0.10.0.

**Current-only amendment (2026-10-02)**: The
[remove-legacy-compatibility feature](../012-remove-legacy-compatibility/spec.md) supersedes
historical weight and per-split threshold readers. Task-backed recovery now requires the
role-marked best Output Model and exact validation-threshold CSV. Historical tasks remain
unchanged, but their old publication shapes are not current inputs.

**Documentation amendment (2026-09-30)**: The standalone split-override wording
reflects current code and configuration composition. The linked original acceptance
records exercise paired current-test execution; they do not establish live non-test
comparison. See the [documentation audit](../../docs/evidence/2026-09-30-instruction-contract-audit.md)
for static checks and limitations.

**Recovery compatibility amendment (2026-10-05)**: The approved
[task recovery contract](../012-remove-legacy-compatibility/contracts/task-recovery.md)
supersedes only current-only checkpoint/threshold recovery restrictions recorded above and
below. Ordered historical threshold payloads, dashboards and checkpoint artifacts are supported
without changing current publication. Explicit maps remain authoritative; present malformed
sources fail, dashboard limitations warn, and both comparison positions use current images
and frozen thresholds with truthful provenance. Completed history remains unchanged.

## Clarifications

### Session 2026-09-30

The approved conversation supplies these decisions; no additional questions were required.

- Progress means native epoch reporting; custom batch scalars are excluded.
- New tasks must contain only performance data artifacts and one native best Output Model. Historical tasks remain unchanged.
- Execution settings are recovered from the current task's configuration. Compared tracked
  models resolve weights and frozen thresholds from their source tasks and record source
  task/model links; current comparison settings remain authoritative.
- Frozen validation thresholds remain performance data. Standalone comparison accepts a split
  override defaulting to test; pipeline comparison uses test. Both roles use identical selected
  images and shared current inference settings.
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

An operator finds only model-performance evidence in artifacts, restores execution settings
from current-task configuration and follows compared models' source-task provenance links.

**Why this priority**: configuration clutter obscures useful evidence and must not become a second replay source.

**Independent Test**: inspect every command's publication inventory and replay using configurations without any configuration artifact.

**Acceptance Scenarios**:

1. **Given** an execution invocation consuming YAML/JSON inputs, **When** publication completes, **Then** temporary numbered YAML, train_data_overrides.json, manifests and receipts are absent from artifacts.
2. **Given** a replayed task, **When** original input paths are unavailable, **Then** canonical task configuration supplies the required settings with existing resolution and sanitization behavior.
3. **Given** compared models with source-task provenance, **When** comparison runs, **Then**
   it records source task/model links and resolves source weights plus exact frozen thresholds;
   current shared comparison inference settings remain authoritative. It does not automatically
   fetch source General parameters or Configuration Objects.
4. **Given** validation-calibrated thresholds, **When** test comparison runs, **Then** both models use the frozen source thresholds on identical current-test images; thresholds are not recalibrated on test.
5. **Given** missing source weights or thresholds, **When** comparison resolves the model,
   **Then** an actionable failure identifies the missing input rather than inventing values.

### Edge Cases

- Incomplete trailing journal records are not reported until complete; corruption or an incomplete final journal fails completion.
- Earlier telemetry may exist on failed runs; it does not authorize successful task completion or final model publication.
- Native final-best validation values retain upstream epoch semantics; equality of epoch indices does not imply duplicate relay events.
- Identical CSV contents publish once; logical aliases remain satisfied.
- Remote overrides, explicit nulls, comments and credential sanitization retain existing configuration-resolution semantics.
- Historical weight and threshold publications are not recovery inputs; current publications are required.

## Requirements

### Functional Requirements

- **FR-001**: Training MUST report installed native epoch losses, available learning rates, validation metrics and epoch time during execution, including DDP, preserving native names and epoch indices.
- **FR-002**: Each invocation MUST own one tracking task; only its owner may report, upload or run native publication callbacks. Nested stages reuse that task.
- **FR-003**: Distributed events MUST be dispatched once, in order, with partial records retained until complete; final native publication MUST wait for a complete validated journal.
- **FR-004**: Callback, journal, computation, upload, flush and interruption failures MUST fail command/task, stop owned relay activity and preserve local outputs.
- **FR-005**: Successful training MUST expose exactly one verified native best Output Model matching the local checkpoint, without a duplicate weight artifact.
- **FR-006**: Native plots and debug samples MUST remain available according to installed callback behavior and explicit plot settings; scalars MUST remain enabled when plots are disabled.
- **FR-007**: New task artifacts MUST contain only canonical ground-truth/prediction CSVs, frozen validation-threshold CSVs, evaluation/comparison workbooks and final performance reports; identical tables MUST be deduplicated.
- **FR-008**: Current execution settings, dataset overrides, normalization and meaningful
  provenance MUST use sanitized Configuration Objects or native General parameters; temporary
  files, manifests and diagnostic receipts MUST remain local.
- **FR-009**: Current-task replay MUST use canonical current-task configuration without
  configuration artifacts and preserve feature 009 resolution behavior. Compared tracked models
  MUST resolve source weights and exact thresholds and record source task/model links without
  automatically fetching source General parameters or Configuration Objects.
- **FR-010**: Comparison MUST retain frozen source validation thresholds, identical paired
  selected-split inputs and shared current comparison inference settings. Standalone comparison
  defaults to test and accepts a split override; pipeline comparison uses test. Model references
  may carry exact supplied thresholds; task recovery requires the current Output Model and
  validation-threshold CSV.
- **FR-011**: Historical tasks, external dependency revisions and unrelated workspace changes MUST remain unchanged.

### Key Entities

- **Invocation owner**: task identity and process authorized to publish.
- **Native event**: ordered epoch/callback observation with enough captured state for native reporting.
- **Best Output Model**: one native model identity linked to the verified local best checkpoint.
- **Performance artifact**: durable result evidence from the command-specific permitted inventory.
- **Replay configuration**: sanitized canonical settings of the current invocation; compared
  source tasks contribute provenance links, weights and thresholds.
- **Frozen threshold table**: validation-calibrated exact thresholds reused for every evaluated
  or compared split; model references may provide exact supplied maps.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In every available multi-epoch acceptance mode, at least one completed epoch's loss is visible before training finishes.
- **SC-002**: A successful training task exposes exactly one downloadable, loadable best model whose bytes equal the local best checkpoint; failed publication never yields successful completion.
- **SC-003**: Every new acceptance task has zero configuration/diagnostic artifacts and only its approved performance inventory.
- **SC-004**: Current-task replay recovers required settings without configuration artifacts;
  paired comparison retains current settings, source links and exact frozen thresholds.
- **SC-005**: Failed/interrupted acceptance scenarios leave no task-owned relay process/thread running; physical DDP unavailable for acceptance is explicitly reported as unverified.

## Assumptions

Installed native callback behavior defines metric series and epoch numbering. No custom batch telemetry, new CLI options, historical deletion, commit, push or release is included. Real execution and mocked tests are reported separately.

## CPU distributed verification amendment — 2026-10-10

The approved amendment adds local regression evidence for User Stories 1 and 2 and
FR-001–FR-005 without changing application interfaces or publication contracts. The
completed implementation and acceptance history above remains a dated record. The
new tasks in [tasks.md](tasks.md) track this amendment separately; dated execution
evidence belongs in `docs/evidence/2026-10-10-cpu-ddp.md`.

A developer can run real distributed native YOLO training on CPU to detect relay,
checkpoint and worker-lifecycle regressions during ordinary repository checks. The
tracking boundary uses a local recording task; no ClearML service, network access,
accelerator, pretrained-weight download or shared dataset is required.

### Additional verification requirements

- **FR-012**: Successful local acceptance MUST execute real native YOLO training and
  validation in both two-rank and four-rank CPU process groups, with actual distributed
  model wrapping, changed model parameters, matching parameters across ranks and
  disjoint, collectively complete training-sampler partitions.
- **FR-013**: The harness MUST preserve installed native training, validation and
  checkpoint loops. CPU adaptations MUST remain test-only and limited to device
  setup, distributed wrapping and final evaluation; production relay behavior MUST
  execute without replacement.
- **FR-014**: During successful training, the invocation owner MUST record native
  epoch telemetry before completion, in journal order and exactly once. Workers
  MUST perform no task creation or publication. Exactly one best-checkpoint record
  MUST be associated with the local recording task, and the actual native checkpoint
  MUST load for inference. This local record does not establish a remote upload.
- **FR-015**: Injected rank-zero, nonzero-rank and owner-callback failures MUST fail
  acceptance, suppress successful terminal model recording and leave no owned
  worker, descendant or relay consumer running. The local harness MUST enforce
  bounded termination rather than hang indefinitely.
- **FR-016**: The CPU distributed suite MUST run in default pytest and commit checks,
  with a marker for focused selection. Only unsupported Linux/WSL or unavailable
  Gloo prerequisites MAY cause a skip; execution failures MUST remain failures.
- **FR-017**: Existing malformed-journal, missing-checkpoint and duplicate-owner unit
  regressions MUST remain. Documentation and evidence MUST distinguish local CPU
  training from accelerator launch, NCCL, AMP and actual ClearML upload verification.

### Additional acceptance outcomes

- **SC-006**: Two-rank and four-rank successful scenarios each demonstrate native
  optimizer updates, synchronized final parameters, valid sampler partitions, live
  owner telemetry and one inference-loadable best checkpoint.
- **SC-007**: Each injected worker or owner failure terminates within the harness
  deadline, records no successful final best-model event and leaves no owned activity.
- **SC-008**: Default collection includes the CPU distributed tests, and focused
  marker selection executes the same scenarios without changing application settings.

This amendment authorizes test and developer-documentation implementation. It does
not authorize dependency changes, production CPU-DDP support or deployment. The
current task's explicit commit/release authorization governs completion; the historical
no-commit statement above describes the original 2026-09-30 implementation scope.
