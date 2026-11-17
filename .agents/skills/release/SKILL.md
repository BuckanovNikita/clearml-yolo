---
name: release
description: Use when preparing a PR for merge, inspecting the automatic release after a merge, or recovering a failed release workflow.
---

# Merge readiness and automatic releases

Paths start at the repository root. `docs/development.md#releases` describes the release
workflow and what it publishes; `docs/development.md#paired-cy-and-queue-check` describes
pairing; model-weight releases follow `docs/development.md#model-weight-releases` under
the authorization rule in `AGENTS.md`.

## Before merge

1. Check the issue's Verification section: every kept line has a status, and none is
   deferred, failed or error. Use `verification-workflow` for gaps.
2. When pairing is selected, run it against the final proposed versions; otherwise write
   the reason it is not selected in the issue.
3. Read the PR title and the commit headers that will land in the squash body, and
   correct any whose Conventional type does not match the release the change should get.
4. Report the PR as ready for a human merge. Done when the issue links the PR and the
   verification statuses.

## After merge

5. Open the release workflow run for the merge and record on the Linear issue the fields
   `docs/development.md#releases` lists. Done when the issue states the version or
   no-version result. The release job establishes no native, GPU, upload or pairing
   outcome.

## Recovering a failed run

6. Read the error and the current remote refs before rerunning anything, then follow the
   recovery paragraph of `docs/development.md#releases`. A conflicting tag needs
   investigation before any rerun; report missing GitHub authorization separately from
   local checks.
7. Never force-push, delete or move tags, or reset unrelated work. Record the recovery and
   its outcome on the issue.
