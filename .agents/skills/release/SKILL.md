---
name: release
description: Use when preparing a release PR, publishing its merged version tag, or recovering a failed release attempt.
---

# Release through a GitHub PR

Read `docs/development.md` (Local releases and Paired CY and queue release check).
The legacy local integration route is retired. Use this replacement only after its
implementation PR is accepted and merged; implementation work never authorizes a release.

1. Establish preparation authorization and separate tag-publication authorization.
   Review the full delta since the previous release, independent review and the linked
   verification record. Required checks must pass or be explicitly waived by the user;
   use `verification-workflow` to resolve gaps. Record source/environment applicability.
2. Select `--pairing required` for dependency/installation changes, queue-consumed
   interfaces or uncertain compatibility; otherwise justify `not-required`. A version
   bump alone does not require pairing. A missing release baseline requires comprehensive
   verification selection.
3. In a clean prepared checkout with authenticated `gh`, invoke `release-prepare` with
   `--expected-tip SHA --verification-record PATH --pairing required|not-required`.
   The source must match fetched `origin/master`. The verification record is included
   in the PR: review it for credentials and private data first. Inspect the release branch
   and PR, or report successful no-version output. Humans merge; agents never merge it.
4. After confirmed human merge and explicit publication authorization, check out the
   exact merged source and invoke `release-publish` with the common arguments plus
   `--pr NUMBER --publish`. Reassess evidence against that source and preserve selected
   pairing. The tool publishes only the annotated code tag, never `master` or artifacts.
5. Report source/final SHAs, PR URL, reused/executed evidence, pairing decision,
   no-version or version result and confirmed remote tag identity. Keep Linear current.

A held lock, dirty/moved tip or mismatched ref requires resolution before retrying.
Inspect failed preparation; recover only this attempt's changes. Retry a valid prepared
branch without regenerating the version. Retry failed publication using the same merged
source and existing matching tag; never overwrite a tag. Keep model-weight releases
separate and follow their procedure only when explicitly requested.
