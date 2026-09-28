# Feature Specification: clearml-yolo 0.3.0

**Feature Directory**: `specs/001-release-030`
**Created**: 2026-09-19
**Status**: Historical 0.3.0 baseline; implemented and subsequently amended
**Input**: Implement the supplied 0.3.0 release plan without publication.

**Post-release amendment (2026-09-28)**: Restore `cy-init-config DIRECTORY [--force]`
as a local initializer for eight editable command examples. The current
[CLI contract](contracts/cli.md) supersedes the original config-generation removal and
eight-entrypoint baseline recorded in the historical plan and task ledger; the package now
exposes nine commands. ClearML task ownership applies to execution commands, not this local initializer.
The subsequent [configuration and publication specification](../002-config-init-release/spec.md)
also governs removal of future-annotations imports and authorizes publication of 0.3.0,
superseding this original specification's non-publication scope.
The later [native configuration specification](../003-ultralytics-config-groups/spec.md)
supersedes the original sparse-mapping and raw-`cfg` design recorded in the historical plan,
research and task ledger. The amended requirements below reflect the current contract, which uses
top-level `ultralytics` and `ultralytics_predict` groups, generates two native group files in
addition to the eight command examples, and rejects raw/non-null `cfg`. The maintained package
version is declared in [pyproject.toml](../../pyproject.toml).

For historical clarity, the original FR-001 accepted raw YAML plus sparse embedded mappings,
FR-005 removed configuration-tree generation, FR-015 prohibited publication, and SC-005
expected eight commands. Those requirements were implemented for the initial 0.3.0 baseline
and then superseded by the linked features; their original intent is retained in the dated
[plan](plan.md), [research](research.md), and [task ledger](tasks.md).

## Context and inventory

Detection practitioners need native model execution plus reproducible evaluation and
production comparisons. Retain training, prediction, dataset ingestion, digital-metrics,
statistical comparison, excluded-class reporting, developer/business workbooks and ClearML.
Remove GPU scheduling, filesystem queues/leases, batch tuning, queue viewing, custom
augmentation JSON and the public tracking-disabled mode. Configuration-tree generation was
part of the original removal inventory and was restored by the
[configuration and publication feature](../002-config-init-release/spec.md).

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

A practitioner trains or predicts through the shared native configuration groups.
**Why this priority**: Existing model settings must survive migration without hidden changes.
**Independent Test**: Equivalent input styles produce equivalent effective model settings.
**Acceptance Scenarios**:
1. Given shared native YAML and prediction overrides, execution respects group and CLI
   precedence, including explicit nulls and values equal to defaults.
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

- **FR-001**: Accept unchanged upstream YAML in `ultralytics/default.yaml`; expose top-level
  `ultralytics` and `ultralytics_predict` groups; preserve explicit prediction nulls and values
  equal to defaults. Raw/non-null `cfg` and nested stage-native mappings MUST fail.
- **FR-002**: Delegate model device, batch, AMP, compilation and execution to the native engine;
  record effective arguments and actual outputs, including distributed parent results.
- **FR-003**: Isolate run outputs; explicitly document pipeline routing and reject conflicting settings.
- **FR-004**: Retain cy, cy-train, cy-predict, cy-metrics, cy-report, cy-compare and cy-ground-truth;
  add cy-val for checkpoint inference plus digital-metrics evaluation.
- **FR-005**: Remove the listed runtime automation, obsolete options, entrypoints, exclusive
  dependencies, tests and instructions. Retain the subsequently restored local initializer.
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
- **FR-015**: Record the original 0.3.0 release with Russian README, migration notes, usable
  Spec Kit metadata, updated agent helpers and verified distributions. The
  [configuration and publication feature](../002-config-init-release/spec.md) later authorized
  and completed GitHub publication; package-index publication remained outside scope.

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
  first run, baseline/candidate, standalone evaluation/comparison, shared native YAML and
  direct group overrides.
- **SC-005**: Both 0.3.0 distributions install cleanly and expose nine commands: eight execution
  commands plus `cy-init-config`.

## Assumptions

- Existing Python/toolchain constraints remain unless evidence requires a change.
- Full comparison requires valid val/test data, accessible checkpoints and baseline thresholds.
- Dataset images remain external. Integration runs follow the environment's access and cleanup contract.
- Physical multi-GPU execution is not a required release gate; native forwarding and worker ownership
  receive automated tests, with real distributed execution recorded as unverified.
