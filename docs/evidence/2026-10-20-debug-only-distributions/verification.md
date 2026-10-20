# Debug-only distributions policy — 2026-10-20

The user requires project `.whl` and `.tar.gz` distributions only for debugging.
Releases use Git commits and annotated tags. Building distributions is not a
release or routine acceptance step, even when generic Python guidance suggests it.

## Scope and plan

Update project instructions, workflow/release guidance, baseline contracts and
the project-owned end-to-end skill. Replace the deployment guide's reliance on
a release wheel with installation from the selected source checkout. Preserve
prior build evidence as historical facts.

The [architecture record](architecture.json) records no module impact.
`scripts/local_release.py` already passes `--skip-build`; hooks contain no
distribution build. No executable change or application test suite is needed.
README and the portable usage skill already describe source-based setup and do
not require release distributions; their usage interfaces are unchanged.

- [x] Validate architecture planning.
- [x] Align current guidance with the user's rule.
- [x] Validate Markdown, links, skill metadata and the scoped diff.
Delivery follows the native documentation commit and Git-only release evaluation;
verify hooks and remote refs before reporting completion.

## Verification

Architecture plan and acceptance validators passed. The documentation checker
checked 49 Markdown files with no issues; Skill Creator metadata validation and
`git diff --check` passed. Reviewed the complete scoped prose diff and confirmed
the existing helper still uses `--skip-build`, with no build command in hooks.
Routine release guidance excludes distribution creation; a concrete packaging or
installation debugging task may create diagnostic files. This is static guidance
validation, not a new live-agent or installation experiment.

The source-install example uses existing pip directory-input and `--no-deps`
syntax; no install or distribution build was run for this documentation change.
Application tests are unnecessary for unchanged runtime/tooling. The only
pre-existing working change is the local source override section in pyproject.toml,
which is preserved through commits. Historical artifacts are not deleted or
relabeled retroactively.

The native changelog helper refreshed the prior committed documentation entry;
that generated change was inspected and is included in the task scope.
