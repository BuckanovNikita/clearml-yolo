---
name: verification-workflow
description: Select verification for a change, final commit, acceptance or release; diagnose deferred checks and report completion evidence.
---

# Select verification

[Development procedures](../../../docs/development.md#verification) own the routing
policy; [Taskfile.yml](../../../Taskfile.yml) owns commands and ordering.

1. Inspect the session status, task-owned diff and host capacity. Prepare the
   worktree's [dependencies](../../../docs/development.md#external-dependencies),
   clear inherited `UV_PROJECT_ENVIRONMENT`, and stop concurrent edits before checking.
2. Complete applicable native Spec Kit analysis and documentation consistency review
   as soon as their inputs exist. Resolve prose corrections and safe formatting before
   committed-tip verification; add no separate documentation gate.
3. Select the automatic route from the staged diff for hooks or latest commit after
   committing: static-only for non-product inputs, bounded selection for test-only
   inputs, ordinary product verification for product source/runtime inputs. Mixed
   changes take the strongest route. Do not broaden a missing test-dependency history
   to the full suite; report its targeted-verification gap.
4. Follow the [commit procedure](../../../docs/development.md#commit-procedure).
   Schedule `prek run --all-files` with hook overrides cleared as the final automatic
   pass; do not first run an equivalent `verify`. Reuse successful evidence while its
   relevant inputs remain unchanged. A prose correction does not invalidate product
   evidence; review fixes rerun affected checks.
5. Explicit test and acceptance commands execute their requested scope regardless of
   classification. For product changes, select the branch mutation report with
   [mutation-testing](../mutation-testing/SKILL.md). Use
   [running-integration-tests](../running-integration-tests/SKILL.md) for live gates;
   [release](../release/SKILL.md) owns local integration and publishing.
6. Report selected checks as passed, failed, deferred, waived or error, with actual
   selectors, source identity and cleanup evidence. Deselection, interruption and
   Task freshness do not establish execution. Record independent review after
   integration and verification for behavior, interface, dependency or policy changes.

Temporary infrastructure or hardware unavailability defers supported checks and blocks
acceptance/integration/release. Continue independent work and retry after availability
changes, without polling. Diagnose configuration, permission and credential errors
with [clearml-yolo-environment](../clearml-yolo-environment/SKILL.md); keep assertion
failures distinct. When only blocked checks remain, report the reason for the user's
decision. A waiver requires user authorization and never counts as a pass.
