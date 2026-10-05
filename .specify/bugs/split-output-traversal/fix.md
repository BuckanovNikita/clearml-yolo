# Fix record: split-output-traversal

Date: 2026-10-04. Status: implemented.

Percent-encode logical split components for filenames, native routes and artifacts; retain manifest identities.

Regression evidence: `tests/test_review_regressions.py, tests/test_metrics.py, tests/test_report.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.
