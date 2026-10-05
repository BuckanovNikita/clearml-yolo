# Fix record: empty-settings-break-replay

Date: 2026-10-04. Status: implemented.

Preserve empty executable replay shapes and native groups; prune optional results separately.

Regression evidence: `tests/test_clearml_session.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.
