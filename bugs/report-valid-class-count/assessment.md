# Bug Assessment: Report availability columns obscure metric tables

- **Slug**: report-valid-class-count (generated)
- **Created**: 2026-10-10
- **Source**: user conversation
- **Verdict**: valid
- **Severity**: low

## Report and agreed behavior

The user reported confusing coverage columns filled with `NA` and requested a
clearer name and compact presentation. The final requested name is
`AP50-valid-class-count`. The user explicitly chose to keep the finite-value count,
including valid zeros, and accepted moving counts below the metric tables.

## Reproduction and cause

Real developer and business builders produce an `ap50 coverage` column with `NA`
in every class row and `1/2` in the mean row for AP50 values `[0.8, NaN]`.
The upstream mean calculator adds these columns only to the mean row; its Excel
writer renders the other empty cells as `NA`. This is a presentation defect,
not a scoring failure. Confidence in the cause is high.

## Proposed remediation

In the project reporting adapter, move generated coverage columns into a two-column
summary below each metric table, legend and population note. Use
`<metric>-valid-class-count` labels, including `AP50-valid-class-count`, and retain
the upstream `valid/eligible` counts. Preserve model-specific and shared comparison
populations, numeric means, missing metric values, formatting and identity metadata.
Apply the layout before identity annotation; leave dependency sources unchanged.

Files: `adapters/reporting/reports.py`, a focused reporting layout helper,
`tests/test_report_class_availability.py`, and the openpyxl ownership allowlist in
`pyproject.toml`. Add real-builder checks for zero/unavailable AP50, one-sided and
empty populations, translated headers, styles, and identity/print round-trips.

## Documentation and verification plan

Update the current contract index, CLI report contract, publication contract,
report identity contract and README report guidance. Existing feature identity
requirements remain applicable after this documented presentation amendment.
Run affected real-workbook tests, lint, types, architecture checks and required
commit checks. Validate changed Markdown and links. Record outcomes in fix.md and
test.md here; preserve installed `.specify/` files.

## Risks and open questions

The adapter must preserve upstream denominators rather than recount padded rows,
recognize custom business translations, and remove obsolete column widths.
No open product questions remain. Historical workbooks are not rewritten.
