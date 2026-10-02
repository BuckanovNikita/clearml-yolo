# Feature Specification: Remove legacy compatibility

**Feature Branch**: `012-remove-legacy-compatibility`

**Created**: 2026-10-02

**Status**: Implemented, verified and independently reviewed

**Completion authorization (2026-10-02)**: After implementation acceptance, the user requested
a full Spec Kit workflow pass, verification, commit and push of all task changes if no blockers
remain. This supersedes the original no-commit/no-push scope below; dependency changes,
deployment and existing-data deletion remain outside scope.
The subsequent instruction to finish also authorizes the proposed one-line archived-link repair
in `.specify/bugs/excel-match-export/test.md`; other protected workflow files remain unchanged.

**Input**: Remove backward compatibility because there are no old-version users.
The user explicitly selected removal of every legacy path, including direct native-dataset
training, and approved amendment of the project constitution.

## User Scenarios & Testing

### User Story 1 - Train from one current input contract (Priority: P1)

Users supply ground-truth CSV for standalone or pipeline training and obtain a reusable
prepared dataset and best checkpoint without a second native-only training path.

**Why this priority**: One input contract reduces configuration and maintenance work.

**Independent Test**: Train from CSV using each supported export format and reject missing input.

**Acceptance Scenarios**:

1. **Given** valid CSV, **When** training runs, **Then** both dataset formats retain source safety,
   cache reuse, dataset replay and model publication.
2. **Given** no ground truth, **When** standalone training is requested, **Then** input validation
   fails before training; a native dataset setting does not provide an alternative.

### User Story 2 - Recover current model publications (Priority: P1)

Users compare completed current runs with validation-calibrated thresholds, without old
checkpoint artifacts or historical threshold payload readers.

**Why this priority**: Recovery must use the same contract as current publication.

**Independent Test**: Recover a current model and exact thresholds, and reject historical-only data.

**Acceptance Scenarios**:

1. **Given** a current completed task, **When** comparison loads it, **Then** weights come from
   its best Output Model and thresholds from its validation CSV regardless of evaluation split.
2. **Given** missing or malformed current publications, **When** loading runs, **Then** it fails
   without using historical payloads or checkpoint artifacts.

### User Story 3 - Configure and read only current behavior (Priority: P2)

Users configure comparison through evaluation settings and read examples for supported inputs.
Maintainers no longer carry migration guides, old aliases or unused compatibility helpers.

**Why this priority**: Code, examples and governing contracts must agree.

**Independent Test**: Compose exported examples, validate unsupported settings, and check links.

**Acceptance Scenarios**:

1. **Given** current evaluation overrides, **When** comparison runs, **Then** they apply without
   duplicate top-level evaluation fields.
2. **Given** unsupported settings, **When** configuration is validated, **Then** strict errors
   identify invalid input without migration-specific branches.
3. **Given** current documentation, **When** examples and links are checked, **Then** no active
   instructions depend on removed interfaces or deleted migration guides.

### Edge Cases

- Missing, duplicate, nonfinite or out-of-range validation thresholds must fail.
- Ambiguous best models and missing downloaded checkpoints must fail.
- Hydra additions cannot silently introduce ignored wrapper or inference keys.
- Canonical explicit cache/output destinations and current dependency integration remain valid.
- Dated evidence and completed history are preserved without claiming old behavior is current.

## Requirements

### Functional Requirements

- **FR-001**: Standalone training MUST require CSV ground truth and remove native-only training.
- **FR-002**: Successful training MUST expose prepared dataset paths and preserve both current
  formats, cache reuse, immutable source data and dataset replay.
- **FR-003**: Task-based recovery MUST use the current best Output Model and exact validation CSV
  only; explicit local weights and supplied threshold maps MUST remain supported.
- **FR-004**: Comparison MUST use one evaluation configuration without top-level legacy overlays.
- **FR-005**: Unsupported configuration MUST fail strict validation without migration branches;
  the unused shared-group prediction-helper parameter MUST be removed.
- **FR-006**: Application cache initialization MUST use canonical settings without the legacy
  ClearML cache alias; unused identity helpers and obsolete naming constants MUST be removed.
- **FR-007**: Current documentation MUST describe supported behavior and remove migration guides;
  release records, completed task history and dated evidence MUST remain intact.
- **FR-008**: Constitution 6.0.0 MUST reflect the approved removal while preserving amendment
  history. Installed workflow tooling and dependency pins MUST remain unchanged.
- **FR-009**: Verification MUST cover the changed behavior, repository checks, documentation
  validation, real CPU/GPU execution when available and current ClearML recovery.

### Key Entities

- **Prepared dataset**: CSV-derived, cache-owned data in either supported export format.
- **Current model publication**: Best Output Model plus exact validation threshold CSV.
- **Evaluation configuration**: Shared matching and scoring settings for both compared models.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All current training scenarios pass and missing CSV fails before training.
- **SC-002**: Current task recovery preserves exact thresholds; every historical-only recovery
  scenario fails rather than selecting an alternative publication.
- **SC-003**: All current examples compose and all changed local documentation links resolve.
- **SC-004**: Repository checks pass; real-run evidence states outcomes and unavailable gates.

## Assumptions

- No old-version consumers need preservation or migration.
- Useful current interoperability, metric plots, artifact deduplication and explicit destinations
  are not legacy compatibility and remain supported.
- No commit, push, deployment, dependency revision change or old-data deletion is authorized.
- Work uses a task branch in the shared checkout with explicit parallel file ownership;
  the existing local dependency-source overrides are preserved.
