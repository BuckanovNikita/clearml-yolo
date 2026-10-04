# Fix record: local-rank-owner-ambiguity

Date: 2026-10-04. Status: implemented.

Reject ownerless rank launch early; require PID and task owner provenance for descendants.

Regression evidence: `tests/test_review_regressions.py, tests/test_native_runtime.py, tests/test_clearml_session.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.
