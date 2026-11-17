---
name: release
description: Use when inspecting automatic code releases, preparing merge readiness, or recovering a failed release workflow.
---

# Automatic releases after merge

Read `docs/development.md` (Local releases and Paired CY and queue release check).
Human merges to `master` authorize the GitHub release workflow to publish a version
commit and annotated tag. Local release commands are retired; agents deliver task
branches and PRs, and humans merge.

1. Before merge, reconcile the delta since the previous release with reviewed verification
   evidence and the explicit pairing decision. Use `verification-workflow` for gaps.
   Required checks must pass or have an explicit user waiver. Complete selected pairing
   against the final proposed versions; record source/environment applicability in Linear.
2. Inspect the workflow result after merge. Confirm its source/final SHAs, no-version or
   version result, and remote commit/tag identities. The metadata-only job does not
   establish native, GPU, upload or pairing outcomes.
3. For a failed run, inspect the error and current remote refs before rerunning the workflow.
   A stale tip requires refreshed `master`; a conflicting tag requires investigation.
   Never overwrite tags, force-push, or reset unrelated work. An already published release
   is a successful no-op. Report unresolved GitHub authorization separately from local checks.
4. Record the workflow URL and outcome in Linear or linked dated evidence. Keep model-weight
   releases separate and follow their procedure only when explicitly requested.

The workflow owns serialization, metadata validation and atomic commit/tag publication.
It creates no GitHub Release, package or deployment. Repository rules must permit its
release commit; resolve missing bot authorization without weakening human branch protections.
