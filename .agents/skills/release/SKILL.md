---
name: release
description: Use when integrating or publishing a release, or recovering failed release attempts.
---

# Release reviewed changes

Read `docs/development.md` (Local releases and Paired CY and queue release check).
Paths start at the repository root; Task and semantic-release own mechanics.

1. Establish local release authorization and separate publishing authorization.
   Review the full change since the previous release, fresh independent review and
   the native verification record. Confirm required checks passed or were explicitly
   waived, including relevant manual evidence; use `verification-workflow` for gaps.
2. Select `--pairing required` for dependency/installation changes, queue-consumed
   interfaces or uncertain compatibility; otherwise justify `not-required` in the record.
   A version bump alone does not require pairing. Missing release baseline requires
   comprehensive selection.
3. Invoke `release-local` or `release-publish` with full immutable `--expected-tip`,
   `--verification-record PATH` and `--pairing required|not-required`. The record is a
   reviewed attestation, not machine-validated proof. Reuse applicable checks; selected
   pairing executes against final versions. Publishing remains separately authorized.
4. Report accepted/final SHAs, reused/executed evidence, pairing decision, version or
   no-version result and remotely confirmed refs.

A held lock or moved/dirty tip requires owner resolution. Inspect prepared files and
refs after version validation failure; recover only this attempt's changes. After
publishing failure, inspect remote refs and retry publication without re-versioning.
Keep model-weight releases separate; their procedure applies only when requested.
