# Workflow transition verification — 2026-11-17

## Scope and source

Working tree: `master`, equal to local `master`; remote references were not fetched.
Instructions now use Linear and GitHub PRs, with optional stacks and human merges.
Spec Kit artifacts are frozen; 18 installed skill files moved intact outside discovery.
Legacy code release execution is suspended pending a PR-based replacement.

## Evidence

- Passed: final automatic `prek run --all-files` with SKIP, PREK_SKIP,
  CY_VERIFY_SCOPE and PRE_COMMIT_ALLOW_NO_CONFIG cleared, after instruction integration.
- Passed: `git diff --check`.
- Passed: byte comparison of all 18 moved skills against HEAD originals; no Spec Kit
  skill remains under `.agents/skills` (also exposed through `.claude/skills`).
- Passed: fresh independent read-only review of the integrated policy against prior
  obligations; no actionable findings. Feature PRs, optional stacks, human merges,
  archive policy, release suspension and preserved safeguards were reviewed.
- Not selected: product/native/GPU tests; this change contains no product implementation.
  Static hooks do not establish live training, upload, GitHub merging or release outcomes.
- Delivery follow-up: the user explicitly authorized commit and PR creation. A clean
  isolated worktree on `docs/sip-64-linear-pr-workflow` contains only this task's changes;
  the original working tree and unrelated files remain untouched. Committed-tip results
  and the PR link are recorded in SIP-64 and the PR after execution. Human merge remains
  outstanding until confirmed by GitHub.

Linear migration evidence and source mappings are recorded separately in
[the migration report](2026-11-17-linear-migration.md). No live test environment was
started or stopped; the pre-existing recorded environment belongs to another task.
