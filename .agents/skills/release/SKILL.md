---
name: release
description: Use when a code release is requested, or when assessing the suspended release route.
---

# Code releases are suspended

Read `docs/development.md` (Local releases). The legacy `release-local` and
`release-publish` commands bypass GitHub PR integration; do not invoke them.
Find the PR-based release tooling follow-up in the Linear clearml-yolo project and
report the suspension. An ordinary implementation request does not authorize replacing
release tooling or publishing tags. Preserve existing releases and unrelated work.

After an explicitly authorized replacement is reviewed and merged, update this skill
with its supported procedure before resuming code releases. Preserve semantic-release,
annotated tags, immutable source checks, locks, applicable verification, selected pairing,
separate publishing authorization and bounded recovery. Model-weight releases remain a
separate explicitly requested procedure in `docs/development.md`.
