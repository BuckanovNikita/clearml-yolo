# Feature Specification: clearml-yolo 0.3.0

**Feature Directory**: `specs/001-release-030`
**Created**: 2026-09-19
**Status**: Implemented; see dated release verification
**Input**: Implement the supplied 0.3.0 release plan without publication.

## Context and inventory

Detection practitioners need native model execution plus reproducible evaluation and
production comparisons. Retain training, prediction, dataset ingestion, digital-metrics,
statistical comparison, excluded-class reporting, developer/business workbooks and ClearML.
Remove GPU scheduling, filesystem queues/leases, batch tuning, queue viewing, custom
augmentation JSON, configuration-tree generation and the public tracking-disabled mode.

## Clarifications

### Session 2026-09-19

The supplied release plan records the prior clarification decisions; no additional
questions are needed. Thin wrapper describes model execution, not evaluation/reporting.
The baseline is the latest completed prod-tagged task excluding this invocation, or an
explicit task/checkpoint. Automatic absence skips comparison; invalid explicit inputs fail.
Candidate thresholds come from val; baseline thresholds are loaded and test never calibrates.
CPU and one GPU are release gates; real multi-GPU execution remains explicitly unverified.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute native detection runs (Priority: P1)

A practitioner trains or predicts using an existing native configuration or embedded values.
**Why this priority**: Existing model settings must survive migration without hidden changes.
**Independent Test**: Equivalent input styles produce equivalent effective model settings.
**Acceptance Scenarios**:
1. Given raw YAML and explicit embedded/CLI values, execution respects their documented order,
   including explicit values equal to defaults.
2. Given a requested device, batch, precision or compilation setting, execution delegates it
   unchanged and records actual effective arguments and output locations.
3. Given conflicting pipeline output settings or removed options, execution fails clearly.

### User Story 2 - Evaluate and compare on current data (Priority: P1)

A practitioner evaluates a checkpoint and compares production and candidate on current test images.
**Why this priority**: Dataset drift and test calibration otherwise invalidate model decisions.
**Independent Test**: A baseline/candidate fixture produces consistent statistical and business counts.
**Acceptance Scenarios**:
1. Given validation and test data, candidate thresholds are calibrated on val once and frozen.
2. Given a baseline, both models infer the same current test images under matching settings;
   exact saved baseline thresholds are used and all reports use these results.
3. Given no automatic baseline, candidate evaluation succeeds with comparison marked skipped;
   invalid explicit baselines or missing required thresholds fail.
4. Given empty images or differing class vocabularies, false positives and exclusions remain visible.

### User Story 3 - Retrieve a complete tracked run (Priority: P1)

A practitioner retrieves settings, model references and every generated output from one task.
**Why this priority**: An incomplete upload must not appear as a reproducible successful run.
**Independent Test**: One invocation owns one task and all required artifacts download successfully.
**Acceptance Scenarios**:
1. Given a full pipeline, every stage shares one task, without callback-created duplicates.
2. Given successful computation, completion waits for required outputs to upload.
3. Given computation, upload failure or interruption, exit is nonzero, task fails and local files remain.
4. Given distributed workers, task creation and uploads remain owned by the parent.

### User Story 4 - Install and migrate the release (Priority: P2)

A user installs 0.3.0 and follows current documentation and examples.
**Why this priority**: Removed entrypoints and fields require an actionable migration path.
**Independent Test**: Clean wheel installation exposes exactly the retained commands and cy-val.
**Acceptance Scenarios**:
1. Given an installed distribution, retained command help and standalone evaluation work.
2. Given the Russian README and migration notes, native settings and pipeline routing are explicit.
3. Given agent-run instructions, preflight, capacity, explicit devices and cleanup remain usable.

### Edge Cases

Invalid native keys, missing checkpoints/images/splits, missing or nonfinite thresholds,
class mismatches, images with no objects, conflicting output paths, interrupted uploads,
first run without baseline, and distributed parent return values are covered by validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Accept unchanged native YAML and embedded native mappings with precedence defaults,
  raw YAML, explicitly supplied embedded values, then CLI; preserve explicit default values.
- **FR-002**: Delegate model device, batch, AMP, compilation and execution to the native engine;
  record effective arguments and actual outputs, including distributed parent results.
- **FR-003**: Isolate run outputs; explicitly document pipeline routing and reject conflicting settings.
- **FR-004**: Retain cy, cy-train, cy-predict, cy-metrics, cy-report, cy-compare and cy-ground-truth;
  add cy-val for checkpoint inference plus digital-metrics evaluation.
- **FR-005**: Remove the listed runtime automation, generated config trees, obsolete options,
  entrypoints, exclusive dependencies, tests, specifications and instructions.
- **FR-006**: Preserve YOLO dataset ingestion and ground-truth/prediction table contracts.
- **FR-007**: Calibrate candidate on val and freeze test thresholds; load baseline thresholds;
  reject missing required thresholds and unsupported evaluation inputs explicitly.
- **FR-008**: Resolve latest completed prod baseline excluding current task, preserve explicit
  task/checkpoint selection, skip only automatic absence and fail invalid explicit selections.
- **FR-009**: Infer both checkpoints on identical current test images with matching settings;
  prohibit historical dashboard comparison across datasets.
- **FR-010**: Preserve statistical methods, exclusions and developer/business workbook formats;
  share evaluated results among builders to ensure consistent counts and thresholds.
- **FR-011**: Require ClearML, own one task per invocation and share it across pipeline stages;
  prevent upstream/worker duplicate tasks, metrics and model uploads.
- **FR-012**: Save source configs, resolved wrapper config, effective model args, dataset config,
  model references and methodology; exclude credentials and dataset images.
- **FR-013**: Upload checkpoints, prediction/truth tables, exact thresholds, metrics, plots and
  reports; track expected stage outputs and complete only after successful required uploads.
- **FR-014**: Fail task and process on computation/upload failure or interruption; retain local outputs.
- **FR-015**: Release 0.3.0 with Russian README, migration notes, usable Spec Kit metadata,
  updated agent helpers and verified distributions; do not publish, push tags or host a release.

### Key Entities

- Run: isolated identity, one tracking task, configuration provenance, enabled stages and manifest.
- Dataset: external image membership, class vocabulary, labels and validation/test split identity.
- Model reference: local checkpoint or tracked task, exact calibrated per-class thresholds.
- Evaluation: frozen thresholds, image membership, matches/counts, exclusions and methodology.
- Artifact: stage, path/name and required upload status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All configuration precedence and removed-option acceptance cases pass.
- **SC-002**: All evaluated test images and per-class counts agree across comparison reports;
  no test-set calibration occurs.
- **SC-003**: Every enabled stage's required artifacts are downloadable from exactly one task;
  induced failures never yield a successful task.
- **SC-004**: Mandatory regression checks pass and dated real CPU/single-GPU evidence covers
  first run, baseline/candidate, standalone evaluation/comparison and both configuration styles.
- **SC-005**: Both distributions install cleanly and expose exactly the eight release commands.

## Assumptions

- Existing Python/toolchain constraints remain unless evidence requires a change.
- Full comparison requires valid val/test data, accessible checkpoints and baseline thresholds.
- Dataset images remain external. Integration runs follow the environment's access and cleanup contract.
- Physical multi-GPU execution is not a required release gate; native forwarding and worker ownership
  receive automated tests, with real distributed execution recorded as unverified.
