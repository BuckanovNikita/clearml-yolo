# Feature Specification: Model identity on dashboards and reports

**Created**: 2026-10-07
**Status**: Approved intent; implementation in progress
**Input**: User-approved plan, “Model identity on every dashboard and report”.

**Presentation amendment (2026-10-10)**: The
[current report contract](../001-release-030/contracts/cli.md) moves availability
columns into valid-class-count summaries before identity annotation. Preservation
requirements below apply to that presentation; metric values and populations do not change.

## User Scenarios & Testing

### User Story 1 - Identify a trained model (Priority: P1)

An evaluator can identify the training source of every newly produced result.
The finalized unique project-local model name and full training task ID travel
with the checkpoint, predictions, evaluations, and reports.

**Independent test**: Train repeated requested names and verify distinct finalized
names; recover each checkpoint and retain its original identity under another task.

**Acceptance scenarios**:

1. Given a name collision, training resolves the name and all reports use that name.
2. Given a recovered checkpoint, evaluation shows the source training task ID.
3. Given stale checkpoint or prediction metadata, processing fails explicitly.

### User Story 2 - Read identified reports (Priority: P1)

Every worksheet and printed page identifies its model; paired reports identify
baseline and candidate separately. Interactive dashboards and plots show captions.

**Independent test**: Generate real multi-sheet workbooks and plots; inspect every
sheet, repeated print titles, and captions while comparing original metrics.

**Acceptance scenarios**:

1. Full/DTRK, evaluation, statistical, developer, and business workbooks identify all sources.
2. Annotated dashboards remain usable for report generation and threshold recovery.
3. Existing headings, formulas, styles, class populations, and pagination are preserved.
4. A missing automatic baseline leaves identified candidate outputs and the skip reason.

### User Story 3 - Label standalone inputs (Priority: P2)

A user evaluating unregistered local inputs supplies a custom model label without
registering a model or inventing a training task ID.

**Independent test**: Evaluate local inputs with custom labels and verify
“Training task: unavailable”; unlabeled inputs without provenance fail clearly.

### Edge cases

Long names, Unicode, formula-like labels, two roles with distinct source tasks,
historical unannotated dashboards, missing provenance, and stale sidecars.

## Requirements

- **FR-001**: Reuse project-local unique naming and persist finalized name, source task ID,
  and checkpoint association; never substitute the current report task ID.
- **FR-002**: Carry identity through prediction provenance, evaluation contexts, and manifests.
- **FR-003**: Accept custom labels, independently for baseline/candidate; require a label
  when provenance is unavailable and explicitly display unavailable training provenance.
- **FR-004**: Display identity on all generated report worksheets, printed pages, and plots.
- **FR-005**: Preserve metrics, formulas, styles, class populations, paths, and artifact names.
- **FR-006**: Read annotated and historical unannotated dashboards using repository adapters.
- **FR-007**: Leave pinned dependencies and historical ClearML artifacts unchanged.

### Key entities

Model identity, checkpoint association, prediction provenance, evaluation context,
paired comparison manifest, and annotated workbook.

## Success Criteria

- Every newly generated worksheet and print-title configuration contains complete identity.
- Recovered and composed evaluations retain the correct source identity in all tested flows.
- Report and threshold readers return unchanged metric populations and values.
- Repository checks, independent review, and native training/publication verification have
  dated evidence, including any limitations.

## Assumptions

Existing ClearML execution requirements remain; custom labels do not require model
registration and do not claim uniqueness. Full task IDs disambiguate projects.
This change affects new outputs only. Existing source provenance takes precedence over
a custom fallback label. Native Ultralytics training diagnostics retain native formatting;
the reporting requirement covers this project's evaluation dashboards and reports.
