# Bug Verification: Compact valid-class-count summaries

- **Slug**: report-valid-class-count
- **Tested**: 2026-10-10
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Reproduction and regression checks

The new real-builder assertions first failed because coverage columns were still
present. After the layout change, the affected report, class availability and
workbook identity modules passed: 20 tests. Real XLSX files from both builders show
the compact summaries, valid zeros, `1/2`, `0/2` and `0/0`, correct own-model/shared
populations, unchanged actual missing metric values, formatting and readable identities.
Source workbook bytes remain unchanged.

The fresh final independent review returned `ship` with no material findings and
independently passed all six real-builder availability cases.

Independent reviews reproduced two unused custom-translation collisions. The expanded
real-builder regressions failed before their lookup corrections; all 20 affected tests
passed after them. An empty shared population omits unconfigured custom difference
metrics upstream; the test preserves that behavior.

Commands: `uv run --no-sync pytest tests/test_report_class_availability.py
tests/test_report.py tests/test_workbook_identity.py -q`, `uv run --no-sync ruff check .`,
`uv run --no-sync mypy .`, and `uv run --no-sync lint-imports`. Lint and strict types
passed; all 27 import contracts were kept. Checks used the existing dependency
environment with the current worktree source selected explicitly; no dependency
source or version was changed.

## Documentation

Reviewed and updated the documentation scope in the assessment. Markdown fences,
whitespace and local file links were checked. Documented execution commands and
configuration examples are unchanged.

## Limits

Verification generates and reads real workbook files locally. It does not claim
native inference, GPU execution, ClearML uploads, or regeneration of historical
reports. No shared service was started or stopped.

## Release checks

The initial full suite passed: 1,379 passed, 30 skipped. The subsequent translation
corrections passed the affected tests above. Implementation commit `59c5aad` then
passed every applicable normal commit hook, including the full pytest suite,
Ruff, mypy and import-linter. No checks were bypassed. Git-tag publication follows
the repository release workflow; its outcome is reported separately at completion.
