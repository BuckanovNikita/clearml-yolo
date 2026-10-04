# Fix record: clearml-failure-self-abort

Date: 2026-10-04. Status: implemented.

Close before fresh-handle failure transition; preserve original exception when cleanup fails.

Regression evidence: `tests/test_clearml_session.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.

Local cleanup OSError also preserves an existing primary exception; cleanup errors still propagate after an otherwise successful call. Two targeted regressions cover both outcomes.
