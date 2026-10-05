# Bug Verification: New and deleted class metrics

- Slug: new-deleted-class-metrics
- Tested: 2026-10-05
- Assessment: [assessment](assessment.md)
- Fix: [fix](fix.md)
- Result: verified

## Summary

The original missing-class failure is reproduced by tests that failed before changes and now pass through real builders and saved XLSX files. New/deleted/disjoint classes retain available values, unavailable cells are NA, and real zeros survive. Aggregation populations match the approved plan.

## Checks Performed

| Check | Command / action | Result |
| --- | --- | --- |
| Original failure, before fix | Parent real-builder integration | 2 failed because new/deleted rows disappeared |
| Parent full regression suite | uv run --no-sync pytest -q | 934 passed, 9 skipped, 4 dependency deprecation warnings |
| Final affected parent suite | uv run --no-sync pytest -q tests/test_comparison_assemble.py tests/test_comparison_workbook.py tests/test_clearml_report.py tests/test_report_class_availability.py tests/test_report.py | 81 passed; includes final saved-disjoint case added after full-suite collection |
| Report-generator full suite | uv run --no-sync pytest -q external/report-generator/tests | Parent observed 96 passed before final 12 normalization cases; implementer final run 108 passed |
| Final report-generator cases | uv run --no-sync pytest -q external/report-generator/tests/test_union_reports.py | Parent observed 25 passed, including 12 normalization cases |
| Real-builder integration rerun | Submodule suite plus tests/test_report_class_availability.py and tests/test_report.py | 104 passed before final normalization cases |
| Parent lint/types/import boundaries | uv run --no-sync ruff check .; mypy .; lint-imports | Passed; 111 typed source files, 9 import contracts |
| Submodule lint/format | Ruff check and format --check on report_generator, tests, create_test_data.py | Passed |
| Whitespace and Markdown | git diff --check, fenced-block/whitespace/local-file link validation | Passed |
| Dependency integration | uv lock --offline; uv sync --locked --offline; importlib metadata | report-generator 0.1.2 installed; lock changed only its version |
| Independent review | Fresh read-only reviewer, 100 focused tests and 12 normalization cases | ship; no blocking findings |
| Git release verification | git ls-remote main and annotated tag | main and v0.1.2 resolve to 8ddd0f7f11d25367f4e71ace77524ebb72257699 |

## Documentation and release

Updated parent and report-generator README guidance, CLI evaluation contract and current-contract index. Revised missing-value comments; validated Markdown/local links. Completed report-generator patch commit and pushed main plus v0.1.2 atomically. Published no release assets, GitHub Release object or registry packages. Parent source/dependency/gitlink/documentation changes remain uncommitted. The original local uv.sources section is restored exactly and unstaged. The digital-metrics checkout remains clean at its approved revision. Sync removed an existing untracked environment package; pi-heif 1.4.0 was restored afterward without changing dependency declarations or lock entries.

## Residual risks

Workbook validation used synthetic dashboard inputs and real saved XLSX outputs. Tracking was mocked; this work does not establish native inference, GPU behavior, ClearML uploads or Excel GUI rendering. Nine opt-in integration tests were skipped in the full suite. No shared services were changed or restarted.

## Recommendation

Close the reported missing-class presentation bug. Report-generator v0.1.2 is published as a Git tag only; review/commit the parent changes separately when requested.
