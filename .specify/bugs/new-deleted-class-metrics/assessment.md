# Bug Assessment: New and deleted class metrics

- Slug: new-deleted-class-metrics
- Created: 2026-10-05
- Source: user report and approved implementation plan
- Verdict: valid
- Severity: medium

## Symptom and reproduction

User requests metrics for new/deleted classes in all workbooks, with NA for the model lacking a class. In an in-memory reproduction, BaseReportBuilder._prepare received candidate classes shared/new and baseline classes shared/deleted; both returned only shared and moved new/deleted to exclusions.

## Root cause

report-generator intersects eligible classes in BaseReportBuilder._prepare and ComparisonCalculator. clearml-yolo comparison assembly removes vocabulary differences and raises when no class can be compared.

## Proposed remediation

Keep per-model eligible inputs separate from union-aligned display rows. Compute model averages and business verdicts over each model's own eligible classes (user selection), with population disclosure. Preserve training filters and numeric missingness; display NA only at rendering. Show one-sided class metrics and unavailable differences without colors in all workbooks. Restrict statistical testing and pooled statistics consistently to shared eligible classes; render unavailable pooled comparisons when none exist. Keep ClearML consumers consistent.

## Files likely to change

- external/report-generator report builders, calculators, writer, tests and documentation
- src/clearml_yolo/comparison/assemble.py and workbook.py; ClearML presentation if required
- affected tests, maintained report contracts, dependency metadata and gitlink

## Tests

Reopen actual XLSX outputs for shared/new/deleted/disjoint classes, missing values versus zero, training exclusions, identities, averages, business verdicts and colors. Verify statistical families and pooled populations. Add real-builder integration and run affected suites/static checks; obtain independent review.

## Documentation and release

Update current contracts and Russian README guidance, validate Markdown/local links. Publish report-generator next patch (expected 0.1.2) after checks and review, then integrate version/gitlink/lock. Preserve digital-metrics pin and local uv sources. No parent commit requested.

## Risks

Different per-model aggregate populations must be explicit. Placeholders must not change denominators or business availability. Missing comparisons are not non-significant results.
