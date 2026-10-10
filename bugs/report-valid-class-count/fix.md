# Bug Fix: Compact valid-class-count summaries

- **Slug**: report-valid-class-count
- **Fixed**: 2026-10-10
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Changes

The report adapter now moves upstream coverage columns into two-column summaries
after each metric sheet's table, legend and population note. AP50 uses the final
requested label `AP50-valid-class-count`; other metrics use the same suffix.
The original valid/eligible fractions, including zero-valued metrics and `0/0`,
are copied unchanged. Obsolete column widths are removed with the columns.

The layout runs before model identity annotation. Source dashboards, historical
artifacts, dependency sources, metric means, business verdicts and actual `NA`
metric cells are preserved. Configured business translations are resolved back to
their source coverage headers. Unexpected coverage layouts or unknown count headers fail
explicitly instead of silently losing data.
Only aggregate fraction cells and coverage translations with an existing base metric
participate in lookup. Unused translations cannot alias numeric metric columns or
hide genuine coverage headers.

## Files and tests

- `adapters/reporting/report_layout.py`: layout and aggregate validation.
- `adapters/reporting/reports.py`: apply layout to both generated report formats.
- `pyproject.toml`: declare the layout module's openpyxl ownership.
- `tests/test_report_class_availability.py`: real workbook checks for valid zeros,
  missing AP50, one-sided/disjoint classes, empty populations, custom headers,
  numeric formatting, identity and print settings.
- `tests/test_report.py`: supply realistic configuration to the existing builder fake.

## Documentation

Updated README report guidance, current contract index, CLI report contract,
publication contract, and report identity spec/contract. No execution command,
configuration example, quickstart, global environment procedure or integration
skill changes are needed: this changes only newly generated report presentation.

## Deviations

The user refined the initial non-zero label to valid-class-count and explicitly
retained zero-valued metrics. No change to the agreed counting semantics.
Workflow artifacts live in `bugs/`, following the existing project precedent and
the instruction to preserve installed `.specify/` files.

## Verification

See [test.md](test.md) for dated checks and limitations.
