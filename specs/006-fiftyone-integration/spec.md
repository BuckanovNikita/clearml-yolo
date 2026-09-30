# Feature Specification: FiftyOne Integration

**Feature Branch**: `master` (no branch created; feature directory is `006-fiftyone-integration`)

**Created**: 2026-09-29

**Status**: Implemented and verified

**Input**: Publish precise existing evaluation results for local persistent visual review through FiftyOne.

## User Scenarios & Testing *(mandatory)*

## Clarifications

### Session 2026-09-29

- Q: Which commands publish by default? → A: `cy`, `cy-predict`, and `cy-metrics` only.
- Q: What persistence and media policy applies? → A: local persistent DB; reference existing media without copying or UI launch.
- Q: What happens on enabled publication failure? → A: fail the owning invocation and retain local outputs.
- Q: How are run and image identities handled? → A: all run fields use ClearML task-ID namespaces; include split; image bytes are accepted immutable inputs after resolved-path validation.

### User Story 1 - Review an eligible run (Priority: P1)

An ML operator runs `cy`, `cy-predict`, or `cy-metrics` with default configuration and receives a local persistent visual-review dataset whose samples reference the existing image media and retain `image_name` and `split`, including backgrounds.

**Why this priority**: It supplies the primary inspection value without changing the current command contract.

**Independent Test**: A fixture run produces one sample per distinct image with referenced paths, expected metadata, raw predictions, evaluated annotations, and a local owner receipt.

**Acceptance Scenarios**:

1. **Given** an eligible command with `fiftyone.enabled=true`, **When** results are ready, **Then** one publisher invocation records a dataset and task-ID-namespaced run fields without launching a UI or copying media.
2. **Given** a background-only image, **When** ground truth is imported, **Then** it has one sample with `image_name`, `split`, and no invented object labels.

---

### User Story 2 - Reuse a completed import safely (Priority: P2)

An operator reruns an eligible command over unchanged inputs and reuses the completed dataset import; a retry after an interrupted publication repairs only its own incomplete run scope.

**Why this priority**: Persistent data is useful only if repeat work is safe and cheap.

**Independent Test**: Completed matching identity reuses records; changed resolved image paths conflict; concurrent publishers serialize per dataset; retry does not delete another task's fields.

**Acceptance Scenarios**:

1. **Given** matching effective-GT hash, schema, prefix identity, and resolved image paths, **When** import is requested, **Then** completed dataset data is reused.
2. **Given** a changed resolved image path for an existing identity, **When** reuse is requested, **Then** the invocation fails before publication.

---

### User Story 3 - Inspect exact evaluated outcomes (Priority: P3)

A reviewer sees raw predictions separately from run-specific evaluated ground truth and predictions, using the exact fixed-threshold digital-metrics match results with TP, FP, FN, filtered statuses and IoU.

**Why this priority**: Visual review must faithfully explain the existing metric result.

**Independent Test**: Representative matches, missed GT, rejected predictions, empty images, normalized GT, and labels/indices agree with the neutral persisted evaluation payload.

**Acceptance Scenarios**:

1. **Given** a split evaluated at frozen thresholds, **When** it is published, **Then** each evaluated annotation has the source identity and exact status/IoU represented by scoring.
2. **Given** cleaned GT differs from the original, **When** the dataset is reused or inspected, **Then** the effective CSV hash is identity while the original hash remains provenance.

### Edge Cases

- A disabled run imports no FiftyOne module and creates no database, receipt, or dataset state.
- Preflight database failure occurs before expensive scoring or inference and fails the invocation while retaining local outputs.
- Dataset completion and run completion are separately marked; incomplete markers are never reused as completed.
- A publisher failure fails an enabled invocation, while nested pipeline stages remain disabled so the pipeline publishes once.
- Image bytes are assumed immutable after path validation; resolved path changes invalidate reuse.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main installation MUST declare FiftyOne, and configuration MUST expose `fiftyone.enabled=true` and `fiftyone.dataset_prefix="clearml-yolo"` for `cy`, `cy-predict`, and `cy-metrics` only.
- **FR-002**: When disabled, eligible commands MUST select a no-op publisher that imports no FiftyOne module and performs no FiftyOne state operation.
- **FR-003**: Only `clearml_yolo.publishing`'s FiftyOne adapter MAY import FiftyOne; a typed replaceable neutral publisher boundary MUST accept persistent evaluation data without requiring FiftyOne types.
- **FR-004**: Publication MUST use a local persistent database, reference existing resolved image media without copying it, and MUST NOT launch a FiftyOne UI.
- **FR-005**: The reusable dataset key MUST include dataset prefix, adapter schema version, and effective GT CSV SHA256. Stored dataset identity MUST include resolved media-path identity, and source GT SHA256 MUST be retained as provenance when cleaning changes GT.
- **FR-006**: Dataset reuse MUST validate each resolved path identity; matching completed imports MUST be reused and any mismatch MUST fail rather than silently merge.
- **FR-007**: A dataset MUST contain one sample per image, including backgrounds, with `image_name` and `split`; image bytes are an accepted immutable-input assumption.
- **FR-008**: Every run field MUST be namespaced by its ClearML task ID. The same task retry MUST be idempotent, and completion markers MUST distinguish durable dataset import from a task's durable run publication.
- **FR-009**: A per-dataset local file lock MUST serialize publishers. Recovery MUST limit mutation to the current task's incomplete run scope and MUST preserve completed or in-progress other-task data.
- **FR-010**: The neutral persisted `EvaluationPayload` MUST be Pydantic, schema version 1, and contain split, image names, thresholds, ground truth, predictions, and matches. Each box MUST retain index, image name, label, `(x1,y1,x2,y2)`, optional confidence, and status; each match MUST retain nullable GT/pred indices, labels, confidence, IoU, and status.
- **FR-011**: Metrics MUST produce the neutral payload from exact digital-metrics fixed-threshold matching. It MUST retain TP/FP/FN/filtered labels, indices, and IoU, separate raw predictions from run-specific evaluated GT/predictions, and MUST NOT rematch or use FiftyOne evaluation.
- **FR-012**: `MetricsResult` MUST expose paths to neutral persisted evaluation payloads; external `digital-metrics` MUST NOT be modified or monkeypatched.
- **FR-013**: The pipeline MUST publish once after its applicable results are ready; nested
  prediction/metrics publication MUST be disabled. Standalone `cy-predict` and `cy-metrics`
  remain eligible owners. `cy-val`, `cy-compare`, `cy-report`, `cy-train` and
  `cy-ground-truth` MUST NOT publish to FiftyOne.
- **FR-014**: Publication MUST preflight the database before costly compute. An enabled
  publication error MUST fail the owning invocation after retaining local outputs. The owner
  MUST write exactly one local receipt and record its meaningful dataset/run link in canonical
  run configuration; the receipt MUST NOT be uploaded as an artifact.
- **FR-015**: The feature MUST preserve nine existing entrypoints, existing ClearML single-task ownership, current frozen-threshold evaluation, and raw artifact contracts.

### Key Entities

- **Dataset identity**: reusable dataset key and evidence for the effective GT, adapter schema, prefix, and resolved media paths.
- **Publication receipt**: local evidence naming the owner task, dataset completion, and run
  completion; its meaningful dataset/run identity is represented in run configuration.
- **Evaluation payload**: neutral persisted record of an evaluated split and its exact scoring correspondence.
- **Run scope**: task-ID-namespaced fields and marker owned by one invocation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each successful eligible fixture publication contains exactly one sample for every distinct input image, including every background image.
- **SC-002**: The disabled-path tests complete without importing FiftyOne or requiring a FiftyOne installation.
- **SC-003**: Fixture publication reproduces each expected TP, FP, FN, filtered status, source index, label, and IoU from the fixed-threshold scoring payload.
- **SC-004**: A completed identical import reuses its dataset without duplicating samples, while a resolved-path mismatch fails before data mutation.
- **SC-005**: A pipeline fixture produces one owner receipt and no nested-stage receipt; an enabled adapter failure fails the invocation and retains local result paths.

## Assumptions

- Existing image bytes do not change behind a stable validated resolved path during reuse.
- The local FiftyOne server/database is available to enabled commands; its preflight is a required operational check.
- Real FiftyOne behavior is verified by smoke and pipeline evidence rather than inferred from unit substitutes.
