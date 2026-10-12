# Shared evaluation and reporting extraction

## Intent and compatibility

Implement the approved extraction plan across clearml-yolo, digital-metrics and
report-generator. Existing public imports, signatures, constructors, return types,
defaults, configuration, command behavior, scientific values and artifact formats
remain compatible. New capabilities are additive; existing callers need no migration.

## User stories

### US1 — Reuse authoritative evaluation (P1)

Provide digital-metrics fixed evaluation, authoritative PR observations, paired
statistics and rendering with explicit paths/captions. Preserve compute_map mutations,
legacy evaluation inputs/results and dashboard tuple/save/show behavior. Match order,
ties, float precision and unavailable values must agree with captured baselines.
Prepared fixed predictions and geometry-valid unfiltered AP predictions remain distinct.
The new rendering route saves each plot once.

### US2 — Reuse reporting without changing workbooks (P1)

Provide report_generator.v2 structured tables, explicit presentation options, a separate
statistical workbook builder and generic OOXML banner/metadata mechanics. Preserve
legacy normalization and numeric-looking-label filtering. Application reports preserve
exact lexical labels, valid/eligible counts below tables, custom configuration and
one-sided missing metrics. Preserve cells, formulas, styles, charts and print settings.
Metadata version 1 remains readable/writable with fingerprint checks and byte-exact
original-content recovery.

### US3 — Integrate without caller migration (P1)

Application adapters consume the new interfaces. Keep selection, calibration, splits,
provenance, source-row lineage, class eligibility, correction families, pooled summaries,
ClearML and FiftyOne publication local. Preserve public application calls, injected
dependency construction, filenames, persisted schemas and publication inventory.
Defer ground-truth deduplication because grouping rules differ.

## Acceptance

Capture evidence before replacing internals. Run existing library suites unchanged,
new API checks, application scientific/report integration and executable architecture
contracts. Exercise all matching/AP strategies, ties, empty populations, paired tests,
lexical labels, one-sided classes, missing values, custom configuration and historical
artifacts. Any unexplained difference blocks that migration. Update dependency revisions
deliberately, document contracts, and obtain fresh independent review after integration.
