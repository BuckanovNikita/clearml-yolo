# Feature Specification: Reusable datasets and native ClearML tracking

**Feature Branch**: `008-dataset-clearml-tracking`
**Created**: 2026-09-29
**Status**: Implemented, verified, and independently reviewed
**Input**: Approved plan for reusable datasets, readable publications, native tracking, and comparison autodiscovery.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reuse prepared datasets (Priority: P1)

An experiment author trains repeatedly from the same CSV without preparing images again,
and recognizes original image filenames in native previews.

**Why this priority**: Repeated preparation wastes storage and delays every experiment.
**Independent Test**: Prepare twice, including two concurrent requests, and observe one dataset.
**Acceptance Scenarios**:

1. Given identical CSV bytes and format, when another run trains, then it reuses the completed dataset without image-content reads, image copying, or NDJSON conversion.
2. Given changed CSV bytes or format, when preparing, then a separate dataset is created.
3. Given original filenames including uppercase extensions, when using NDJSON training, then previews retain those filenames.
4. Given interrupted preparation, when retried, then no partial dataset is consumed and preparation can finish.

### User Story 2 - Inspect native training and model (Priority: P1)

An experiment author views native training metrics, plots, image previews, and one downloadable best model with accurate metadata.

**Why this priority**: These are the primary experiment and model inspection surfaces.
**Independent Test**: Train, download the native best model, and compare fields with its checkpoint.
**Acceptance Scenarios**:

1. Given a training invocation, when native callbacks run, then they reuse its single task and publish native metrics, plots, previews and best model.
2. Given workers or an ended invocation, then workers cannot publish and global settings remain unchanged.
3. Given failed native registration or upload, then the command and task fail, retaining local outputs.

### User Story 3 - Read useful experiment publications (Priority: P1)

An experiment reader downloads canonical tables and final workbooks without diagnostic payloads or duplicates.

**Why this priority**: Publications must explain results directly.
**Independent Test**: Compare each command's exact publication inventory with the contract.
**Acceptance Scenarios**:

1. Given a completed stage, then canonical data, row-level evidence and metadata tables are
   downloadable as CSV, while published tabular XLSX contains metric tables only; locally
   retained dashboards and final report workbooks keep their established XLSX formats.
2. Given an actual empty prediction result, then its valid header-bearing CSV is retained.
3. Given configuration overrides, then one nonempty canonical run configuration and consumed dataset/report configurations support replay; native General owns training arguments.

### User Story 4 - Discover compared model inputs (Priority: P2)

An evaluator compares task-referenced models using their best checkpoint and frozen validation
thresholds on identical current images from the selected split. Standalone comparison defaults
to test; pipeline comparison uses test.

**Why this priority**: Comparison must remain usable across new and historical runs.
**Independent Test**: Compare new native-model and historical artifact tasks, and explicit local models.
**Acceptance Scenarios**:

1. Given source task IDs, then best model selection is explicit, labels and architecture come
   from checkpoints, and full-precision thresholds prefer source validation tables with
   historical per-split payloads retained for compatibility.
2. Given automatic baseline lookup, then the latest completed prod task excluding the current task is used; no matching task skips comparison.
3. Given an invalid explicit reference, then comparison fails. Local models remain supported with explicit exact thresholds.
4. Given source tasks, then the comparison records links and shared current settings without
   copying model training configurations or recalibrating the selected comparison split.

### Edge Cases

- Reject missing requested splits, unsafe filenames, and NDJSON label-stem collisions before publication.
- Incomplete or corrupt cache entries are never consumed; rebuild under exclusive entry ownership.
- Concurrent builders and consumers cannot observe partial files or conflicting native repairs/cache writes.
- Missing or ambiguous best models and missing thresholds fail explicit references.
- Failed artifact/model uploads, flushes and interruptions cannot produce completed tasks.
- Skipped stages declare only publications they actually own; historical tasks are never modified.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cache identity MUST depend only on CSV bytes, format and preparation version; reuse MUST NOT read image contents or mtimes or repeat copying/conversion.
- **FR-002**: NDJSON training MUST preserve original filenames and extension casing; flat naming remains compatible; label-stem collisions MUST fail.
- **FR-003**: Cache construction MUST serialize per entry, publish atomically, validate completion and required files/splits, recover interrupted builds, and protect concurrent consumers from native repair/cache writes.
- **FR-004**: Training and pipeline commands MUST expose a shared dataset cache location with an
  explicit XDG cache or `CY_HOME/.cache` default; run cleanup MUST NOT delete shared entries;
  image corrections require explicit invalidation. Native YAML training MUST stage real image and
  label copies in the workspace cache before native repair/cache writes touch them.
- **FR-005**: The invocation owner MUST enable every installed native ClearML callback with one existing task; workers MUST NOT create tasks or publish; runtime settings MUST be restored without changing global settings files.
- **FR-006**: The same native best Output Model MUST receive accurate available name, task/project, framework, design, labels, tags, description, lineage and checkpoint/version/input metadata; unknown/server-owned fields and production readiness MUST NOT be invented.
- **FR-007**: Completion MUST verify required artifact and native-model registration/upload/flush; all computation, registration, upload, flush and interruption failures MUST fail task and command while retaining local output.
- **FR-008**: Downloadable artifacts MUST follow the explicit readable inventory: canonical
  truth/prediction CSVs, full-precision validation-threshold CSVs, CSV sidecars for row-level
  matches, thresholds, exclusions and methodology, tabular XLSX containing only dashboards or
  metric tables, and final report workbooks. Evaluation XLSX contains summary, per-class and
  confusion matrix tables; comparison XLSX contains only the comparison table. Diagnostic JSON, raw
  metrics, manifests, archives, NDJSON, model duplicates, plot files and configuration copies
  remain local. JSON payloads/configuration and PNG diagnostics retain their formats.
- **FR-009**: One nonempty run configuration MUST contain wrapper/shared inference/evaluation settings, source links and meaningful requested/effective differences. Native General owns training arguments. Only consumed dataset and explicit report configurations remain separately. Commented YAML remains local and canonical configurations support remote clones.
- **FR-010**: Comparison MUST explicitly resolve the source best model, read checkpoint
  labels/architecture and exact source validation thresholds, accept exact supplied thresholds,
  and retain historical checkpoint/per-split-threshold readers.
- **FR-011**: Comparison MUST record source task/model links and shared settings, paired
  current selected-split inference, counts, exclusions and methodology without copied source
  training parameters or selected-split recalibration. Standalone defaults to test; pipeline uses test.
- **FR-012**: Automatic prod selection/exclusion/skip and invalid-explicit-reference errors MUST remain; local models require exact explicit thresholds.
- **FR-013**: Existing 007 behavior, immutable historical tasks, pinned digital-metrics and all nine entrypoints MUST remain compatible except the explicitly changed publication/cache contracts.

### Key Entities *(include if feature involves data)*

- Prepared dataset: content identity, format/version, completion metadata, split membership, original filenames, reusable files.
- Invocation: one task owner, requested/effective settings, required publication receipts retained internally.
- Published model: native best checkpoint, truthful metadata, optional known lineage, source links.
- Evaluation: result CSVs, exact frozen thresholds, CSV evidence/metadata sidecars, metric-only
  workbooks and provenance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two repeated and two concurrent preparations of one input produce one complete dataset with zero repeat copies/conversions; changed inputs produce distinct entries.
- **SC-002**: Every successful training invocation has exactly one task and one native best model; downloaded weights load and metadata matches actual training/checkpoint data.
- **SC-003**: All command inventories match the publication contract, including skipped stages and valid empty results, with zero diagnostic or duplicate publications.
- **SC-004**: New and historical model comparisons preserve every frozen threshold and use
  identical images from the selected split; every injected publication/registration/flush/
  interruption failure is unsuccessful.

## Assumptions

- Images are immutable; identical CSV bytes reference the same images, including when the CSV is moved.
- CSV identity deliberately excludes image hashing and mtime invalidation. Cache invalidation is explicit deletion while no run uses the entry.
- Shared cache consumers use a filesystem supporting process locks and atomic directory rename.
- Automatic cache locations follow the maintained
  [filesystem ownership contract](../../docs/filesystem-policy.md); explicit cache selections
  remain valid anywhere.
- Native ClearML and Ultralytics are installed project dependencies; service access is required for real-run acceptance.
- Historical tasks and unrelated working changes remain untouched. No commits, pushes or issues are requested.

## Clarifications

### Session 2026-09-29

The supplied plan resolves all material product choices; no additional questions were required.
Original filenames apply to NDJSON; flat naming remains compatible. Original image content is
immutable. Native previews are authorized. Full precision thresholds come from validation,
never test. Local models and historical artifacts remain supported. Native write safety,
metadata API details and exact file interfaces are implementation research decisions.
