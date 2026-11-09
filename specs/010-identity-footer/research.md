# Research: Identity Footer for Excel Reports

## R1. Where the footer mechanics live

- **Decision**: Add an opt-in bottom placement to `report_generator.v2.annotate_workbook`
  through new keyword-only parameters: `placement="top"|"bottom"` (default `"top"`),
  `banner_links` (one optional URL per line) and `page_footer` (optional text). With
  `placement="bottom"`, an empty `banner_lines` is accepted, producing a metadata-only
  envelope.
- **Rationale**: The generic OOXML annotation, fingerprint and recovery mechanics already
  belong to report-generator (docs/shared-evaluation-reporting.md). Bottom placement needs
  none of the coordinate shifting that prepend uses, so the existing prepend path stays
  byte-for-byte unchanged for current callers.
- **Alternatives**: CY-only OOXML editing after upstream annotation was rejected: it would
  duplicate the fingerprint and envelope mechanics and invalidate the package fingerprint.
  Writing footer rows before annotation was rejected: they would become part of the
  recoverable "original" and readers would see them as data.

## R2. Footer start row

- **Decision**: footer start row = max(last `sheetData` row, last merged-range row, last
  drawing anchor `to/row` (two-cell) or `from/row` + extent (one-cell) for the sheet's
  drawing part) + 2. An empty sheet starts at row 2. The print area, when defined, is
  extended down to the footer rows and widened to the merged footer width (final area only). Column span and merges follow the existing
  banner width rule (at least A:H).
- **Rationale**: digital-metrics dashboards and confusion matrices can anchor charts below
  the table. Using the sheetData row alone would place footer cells under a chart.
- **Alternatives**: sheetData only (rejected: overlaps charts).

## R3. One footer block across the two envelopes

- **Decision**: The identity envelope owns the visible footer and the page footer. When
  identities exist, CY's `annotate_workbook` runs the presentation (alias) envelope with no
  visible lines (metadata only, bottom mode). It appends the alias notice to the identity
  footer lines when any label was aliased. Without identities, `humanize_workbook` writes
  the alias notice as a bottom footer with no page footer.
- **Rationale**: This gives a single contiguous block and a single `<headerFooter>` writer.
- **Alternatives**: Two stacked blocks with a gap (rejected: noisy, and two writers would
  compete for the page footer).

## R4. Page footer text

- **Decision**: `<Role>: <name> · Training source: recorded|unavailable`, with roles joined
  by ` | `, written to `oddFooter` left section as `&L<text>`. `&` is escaped as `&&`. The
  whole footer string is limited to 255 characters; when longer, the text is truncated at a
  character boundary that never splits an `&&` escape and ends with `…`. Original sheets
  have no `<headerFooter>` today (none in src, report-generator or digital-metrics). If one
  exists, other sections are preserved and only `oddFooter` is replaced.
- **Rationale**: Excel rejects header/footer strings over 255 characters. Print titles only
  repeat top rows, so they can't carry a bottom footer.

## R5. Link construction and port placement

- **Decision**: New core value object `IdentityLinks(model_url, task_url)` with optional
  http(s) URLs. New tracking-port method `TrackingSession.identity_links(identity)`. Its
  ClearML implementation in `adapters/clearml/` builds:
  - the task URL with `Task.get_task_output_log_web_page(task_id, project_id=None)`, which
    gives a `*` project segment;
  - the model URL as `<Session.get_app_server_host()>/projects/*/models/<model_id>`.
  It returns empty links, with no SDK call, when there is no current ClearML task. It logs
  and returns empty links on SDK failure. Application use cases pass
  `links: Mapping[role, IdentityLinks]` into `ReportRenderer.annotate_workbook`,
  `ReportRenderer.write_evaluation_workbook` and `EvaluationWriter.render_evaluation`.
  Reporting adapters never import ClearML.
- **Rationale**: The constitution and `.importlinter` assign ClearML ownership to
  `adapters/clearml`. Application use cases depend on ports. `check_min_api_version` may
  contact the server, so it is only reached when the invocation already owns a live session.
- **Alternatives**: A resolver callable injected into reporting adapters (rejected: a hidden
  cross-adapter bridge). Storing URLs in `ModelIdentity` (rejected by user decision: built at
  render time).
- **Open check**: verify the `/projects/*/models/<id>` form against the stand during
  implementation (T-live), not only at final acceptance.

## R6. Readers and ordering

- **Decision**: No reader change is needed. All in-repo workbook readers go through
  `deannotated_workbook`/`read_dashboard` (`reports.py`, `metrics`), and `count_issues`
  applies counts before annotation (`render_evaluation`, `build_reports`). Naive external
  `pd.read_excel` would read footer rows as trailing rows; this is documented in the
  contract, as before for top banners (which shifted the header instead).

## R7. Contract tests that intentionally change

- `tests/test_shared_extraction_compatibility.py`: the pre-extraction fixture expects
  banner cells at A2/A4. Its expectation transform is updated to the footer layout, and
  the original-recovery equality stays.
- `tests/test_workbook_identity.py::test_banner_all_sheets_preserves_references_and_print_structure`
  becomes a footer test: no shift, no print titles, and a page footer is present.
- Upstream `tests/test_v2_workbook.py` prepend tests must pass unchanged. This is the
  legacy-interface evidence that `docs/development.md` requires for a revision bump.

## R8. Revision bump provenance

- The new report-generator commit is local. Bumping the approved revision in
  `docs/development.md` points at a commit that fresh clones cannot obtain until
  report-generator is pushed, which needs separate authorization. Record this in the
  ledger and raise it at delivery.
