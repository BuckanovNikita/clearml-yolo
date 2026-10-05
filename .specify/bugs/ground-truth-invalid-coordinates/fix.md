# Fix record: ground-truth-invalid-coordinates

Date: 2026-10-04. Status: implemented.

Reject nonfinite/out-of-native-tolerance labels with file/line diagnostic; retain edge clipping.

Regression evidence: `tests/test_review_regressions.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.
