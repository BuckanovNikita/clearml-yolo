# Feature Specification: Identity Footer for Excel Reports

**Feature Branch**: `master` (no feature branch requested)

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Move model identity information such as `model: train-brave-willow` and `Training task: <id>` in all Excel reports from the top to the bottom of the sheet, without touching table headers, and turn ClearML names and identifiers into clickable links where possible."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tables start at the top of every report sheet (Priority: P1)

An analyst opens any Excel report produced by the application: an evaluation
workbook, a metric dashboard, a defect-tracking dashboard, a confusion matrix, a
paired comparison workbook or a candidate-only workbook. Each worksheet starts with
its table header in the first row, exactly as in the original table. Filters, sorting,
copy-paste and spreadsheet formulas work without first skipping banner rows. The
model identity and any class-alias notice appear in an identity footer below all
sheet content.

**Why this priority**: Banner rows above the data push headers down and break the
usual spreadsheet workflow on every sheet of every report. This is the main request.

**Independent Test**: Generate each report kind and open every worksheet. The header
is in row 1, and every data cell matches the unannotated table at the same coordinate.
The identity footer starts after one empty row following the last used row.

**Acceptance Scenarios**:

1. **Given** an evaluation with a recorded model identity, **When** its reports are
   written, **Then** every worksheet keeps its original table coordinates and ends with
   an identity footer that names the model.
2. **Given** a sheet with count or availability rows below the main table, **When**
   the report is written, **Then** the identity footer appears below those rows and
   overlaps no content.
3. **Given** a workbook whose class labels received readable aliases, **When** it is
   written, **Then** the alias notice is part of the identity footer, not a row above
   the data.
4. **Given** a paired comparison, **When** its workbook is written, **Then** the footer
   identifies the baseline and the candidate separately, by role.

---

### User Story 2 - Open the ClearML source of a model from the report (Priority: P2)

From the identity footer, the analyst clicks the model name to open that model's
ClearML page. They click "Training task: open in ClearML" to open the task that
trained it. The links carry exact identifiers. The visible text stays readable and
never shows raw identifiers or digests.

**Why this priority**: The links replace copying opaque identifiers by hand.
Placement (P1) is useful even without links.

**Independent Test**: Generate a report for a model with recorded training-task and
model identifiers while a ClearML session is configured. Each link resolves to the
matching ClearML web page. The visible text contains no identifier or digest.

**Acceptance Scenarios**:

1. **Given** a recorded model identifier and an available ClearML web host, **When**
   the report is written, **Then** `<Role>: <model name>` links to that model's
   ClearML web page.
2. **Given** a recorded training-task identifier and an available ClearML web host,
   **When** the report is written, **Then** `Training task: open in ClearML` links to
   that task's ClearML web page.
3. **Given** no ClearML session or web host at report time, or a link that cannot be
   built, **When** the report is written, **Then** the footer shows the plain lines
   `<Role>: <model name>` and `Training source: recorded` (or `unavailable`). The
   report succeeds, and the missing link is noted only at DEBUG level.
4. **Given** any report, **When** it is written, **Then** no link points to the task
   that produced the report itself.

---

### User Story 3 - Printed pages still identify the model (Priority: P3)

The analyst prints or exports a multi-page worksheet to PDF. Every printed page
carries a plain-text page footer that names each model role and its training-source
status, so a loose page can still be attributed.

**Why this priority**: This preserves an existing guarantee (identity on every
printed page) that the old repeated top rows provided.

**Independent Test**: Inspect the page setup of every worksheet for the page footer
text, and check that no repeated print-title rows are defined for the footer content.

**Acceptance Scenarios**:

1. **Given** an annotated worksheet, **When** it is printed, **Then** each page footer
   reads `<Role>: <model name> · Training source: recorded|unavailable` for every role.

---

### Edge Cases

- An empty worksheet, or one holding only a chart: the footer starts at row 2 after an
  empty row 1. Charts and images keep their anchors.
- Long or Unicode model names and labels that look like formulas: the footer text is
  shown literally and never evaluated as a formula. A page footer escapes characters
  that are special in page-footer syntax.
- Annotating an already annotated workbook again starts from the authenticated
  original. The result is identical, with no duplicate footer.
- Historical workbooks with top banners stay readable. Their original metrics recover
  exactly, and readers do not mistake them for the new layout.
- An annotated workbook edited after annotation is still rejected before its metrics
  are read.
- A model identity without a model identifier or training-task identifier shows the
  available lines as plain text.
- A web host that is not `http` or `https` produces no link.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every Excel report that the application annotates with a model identity
  or class-alias notice MUST leave each worksheet's original cells, header row, merged
  ranges, formulas, defined names, conditional formats, charts and images at their
  original coordinates.
- **FR-002**: The application MUST place the visible model identity and any alias
  notice in an identity footer that starts after one empty row following the last used
  row of each worksheet, in the first column, with the existing wrapped banner style.
- **FR-003**: For each model role, the identity footer MUST show `<Role>: <model name>`.
  When training-source provenance is recorded and a link can be built, the next line is
  `Training task: open in ClearML`; otherwise it is
  `Training source: recorded|unavailable`.
- **FR-004**: `<Role>: <model name>` MUST link to the model's ClearML web page when a
  model identifier is recorded and the ClearML web host is known at report time.
- **FR-005**: `Training task: open in ClearML` MUST link to the training task's ClearML
  web page, built from the recorded training-task identifier and the ClearML web host
  known at report time.
- **FR-006**: When a link cannot be built (no ClearML session, unknown host, a
  non-HTTP(S) host or any URL-building failure), the line MUST render as plain text.
  The report MUST NOT fail for this reason, and the condition MUST be logged at DEBUG.
- **FR-007**: Visible cells and page footers MUST NOT show task identifiers, model
  identifiers or checkpoint digests. Exact identifiers stay in the hidden workbook
  identity metadata and machine provenance, with the existing schema version.
- **FR-008**: No identity footer link may point to the task that produced the report.
- **FR-009**: Each annotated worksheet MUST carry a plain-text page footer naming every
  role, its model name and its training-source status. Footer content MUST NOT rely on
  repeated top print-title rows.
- **FR-010**: Original workbook bytes MUST stay recoverable byte-exactly. Fingerprint
  validation MUST still reject annotated workbooks edited after annotation. Readers MUST
  accept both the historical top-banner layout and the identity footer layout.
- **FR-011**: Re-annotation MUST be idempotent and start from the authenticated
  original.
- **FR-012**: The shared workbook-annotation dependency MUST offer the footer
  placement, hyperlink lines and page footer as an opt-in addition, without changing
  the behavior of existing callers that prepend banners.
- **FR-013**: Reports MUST retain the model's original per-class annotation counts
  for every prepared dataset split, excluding background rows and preserving lexical
  class labels. Training eligibility on every evaluated split MUST use that model's
  original `train` population, never the current evaluation population.
- **FR-014**: Evaluation and comparison workbooks MUST include a `Dataset counts`
  worksheet distinguishing original dataset counts from current evaluation counts
  and identifying baseline and candidate separately where applicable.
- **FR-015**: Count recovery MUST work in a fresh invocation for models trained with
  CY 0.25.0 onward using the original training task's `gt_csv`, after verifying that
  the selected checkpoint belongs to that task and matches the claimed hash. New
  training MUST associate counts with the final checkpoint bytes after metadata
  binding. Recovery MUST NOT modify historical ClearML records.
- **FR-016**: Missing, malformed, unreadable or unverifiable count evidence MUST
  remain explicitly unknown, with a diagnostic. A missing class may mean zero only
  within a verified complete split population. Existing exclusion and issues-sheet
  behavior MUST remain intact when counts are unknown.

### Key Entities

- **Identity footer**: The readable model identity and source links placed after a
  report's data, leaving table headers in place. Exact identifiers stay in provenance.
- **Model identity**: A model's display name and recorded source identifiers (training
  task, model, checkpoint digest), stored in hidden workbook metadata.
- **Identity link**: An optional exact ClearML web address for a model or training
  task, derived at report time and never stored as identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of generated report worksheets, the original table header is in
  row 1, and every original cell value is unchanged at its original coordinate.
- **SC-002**: In 100% of generated reports with recorded identifiers and a reachable
  ClearML web host, each footer link opens the matching model or training-task page.
- **SC-003**: No visible cell or page footer in any generated report contains a task
  identifier, model identifier or checkpoint digest.
- **SC-004**: Report generation succeeds in 100% of runs without a ClearML session, and
  the footers contain plain text.
- **SC-005**: Original metrics recover byte-exactly from every new and historical
  annotated workbook, and edited annotated workbooks are rejected 100% of the time.

## Assumptions

- The ClearML model web page uses the form `<web host>/projects/*/models/<model id>`.
  The task page uses ClearML's own task web-page builder.
- Links are built while the report is written. Workbooks written earlier are not
  rewritten. Readers continue to accept their top-banner layout.
- The report-generator dependency owns the generic workbook mechanics. Changing its
  approved source revision is authorized for this feature. digital-metrics is unchanged.
- Multi-GPU DDP verification is waived on this single-GPU host.
- Work proceeds on `master` with local commits only. Pushing requires separate
  authorization.
