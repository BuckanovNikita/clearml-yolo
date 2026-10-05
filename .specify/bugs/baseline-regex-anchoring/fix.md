# Fix record: baseline-regex-anchoring

Date: 2026-10-04. Status: implemented.

Group pattern within absolute whole-name anchors.

Regression evidence: `tests/test_review_regressions.py, tests/test_clearml_models.py`. Historical review artifacts remain uncommitted.

Documentation update: affected maintained contracts under `specs/001`, `004`, `006`, `010`, `013` reviewed and updated together. Dependency pins unchanged. No commits or publication performed by implementer.

## PCRE boundary followup

Independent review identified that MongoDB's PCRE permits a terminal newline before `\Z`,
unlike Python's regex engine. A PCRE whole-record oracle reproduced the remaining failure
(one failed, three passed). The expression now adds a portable strict-end negative lookahead,
rejecting terminal-newline names in both engines while preserving deliberate regex patterns.
