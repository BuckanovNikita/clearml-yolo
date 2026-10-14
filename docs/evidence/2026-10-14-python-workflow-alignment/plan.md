# Shared Python workflow alignment

Date: 2026-10-14. Baseline: `665dfd3` on master.

## Intent and architecture

Adopt `python-project-workflow` within the existing Spec Kit feature and bug
routes. The native process keeps stage order, artifacts and status; the shared
skill supplies Python compatibility, architecture, verification and release
evidence. Align authorization and proportionate collaboration without changing
application behavior, dependency sources, installed framework tooling or checks.

The adjacent [architecture record](architecture.json) records `impact: none`.
Inspected AGENTS, workflow/development guidance, pyproject, hooks and release
helper. Python 3.12, uv_build, Hydra entrypoints and existing import contracts
remain authoritative. This task changes workflow prose and dated evidence only.
Public CLI/API/configuration and the portable usage skill need no changes because
their behavior and invocation contracts are unaffected.

The original checkout contains unrelated queue/GPU/testing work, development
documentation and local dependency overrides. Work in an isolated checkout;
preserve all of that work and reconcile against the inspected baseline.

## Ownership and tasks

The parent owns clearml-yolo documentation. Bounded delegates independently own
cveta2 and ed-killer documentation in separate worktrees and may not delegate.
Each repository preserves its native workflow. Parent integration and checks
precede fresh independent review, architecture acceptance and native delivery.

- [x] Inspect current guidance, code/configuration contracts and existing work.
- [x] Validate the no-impact planning record before policy edits.
- [x] Align lifecycle discovery, authorization and collaboration guidance.
- [x] Check changed Markdown, local links/anchors, examples and complete diff.
- [x] Obtain fresh independent review and validate architecture acceptance.
- [ ] Commit task-owned changes, evaluate native release and verify pushed refs.

## Acceptance

Run both phases of the shared architecture validator with this repository root.
Run Markdown checks and a local-link/anchor check over changed guidance and new
nested evidence; run `git diff --check`. Review routing for features, bugs,
resumed work, docs-only work, Plan mode, explicit stopping points, missing skills
and docs-only release evaluation. Record actual results in
[verification.md](verification.md).

Retain mandatory native hooks and release recovery. Commits use Conventional
Commits, preserve local source overrides and never resolve dependencies as part
of that preservation. A documentation-only release evaluation may create no tag.
Publish only the intended branch and any exact new Git version tag; no GitHub
Release, package assets, registry publishing or deployment.
