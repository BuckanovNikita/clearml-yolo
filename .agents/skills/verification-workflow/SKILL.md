---
name: verification-workflow
description: Use when verifying changes, committing, reporting completion, or diagnosing deferred checks.
---

# Select verification

Read `docs/development.md` (Verification, External dependencies and Commit procedure);
`Taskfile.yml` owns commands. Paths start at the repository root.

1. Inspect session status, task-owned changes and host capacity. Prepare dependencies,
   clear inherited `UV_PROJECT_ENVIRONMENT`, and finish concurrent edits.
2. Complete applicable native Spec Kit analysis and documentation consistency review
   once inputs exist. Resolve prose and formatting before committed-tip verification;
   add no separate documentation gate.
3. Let hooks classify staged changes and post-commit checks classify the latest commit:
   non-product inputs get static checks, tests get bounded selection, product/runtime
   inputs get product verification. Mixed changes take the strongest route. Missing
   test-dependency history is a reported gap, not a full-suite fallback.
4. Follow the commit procedure, then run `prek run --all-files` with hook overrides
   cleared. Avoid an equivalent preceding `verify`. Reuse checks whose inputs remain
   unchanged; prose corrections preserve product evidence, and review fixes rerun
   affected checks.
5. Explicit test/acceptance commands retain their scope. Use `mutation-testing` for
   product branch reports, `running-integration-tests` for live gates and `release`
   for integration or publishing.
6. Report passed, failed, deferred, waived or error with selectors, source identity and
   cleanup evidence. Deselection, interruption and Task freshness prove no execution.
   Behavior, interface, dependency and policy changes need independent review after
   integration and verification.

Unavailable supported infrastructure/hardware defers checks and blocks acceptance,
integration and release. Continue independent work; retry when availability changes,
without polling. Use `clearml-yolo-environment` for configuration, permission or
credential errors; assertion failures remain failures. When only blocked checks remain,
report the reason for the user's decision. Only the user can waive a check; a waiver
is never a pass.
