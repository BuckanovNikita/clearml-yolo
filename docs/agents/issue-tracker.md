# Issue tracker: Linear and GitHub PRs

Linear team `SIP` hosts several projects; create every issue for this repository in
project `clearml-yolo`. Linear owns requirements, plans, acceptance criteria, dependencies,
ownership, discussion and status; resolve an issue by its identifier or URL. GitHub PRs in
`BuckanovNikita/clearml-yolo` own review and delivery. Link issues and PRs both ways.

## Issues

Start each new issue from the [issue template](issue-template.md). An issue records the
outcome, scope, plan where needed, blockers, compatibility constraints, acceptance
criteria, selected verification and evidence, plus the assumptions made and deviations
from the plan. Inspect current source and configuration before relying on claims in older
issues.

Lifecycle states:

| State | When |
| --- | --- |
| Backlog | Captured, not yet planned |
| Todo | Planned and ready to start |
| In Progress | Work started on a task branch |
| In Review | PR open, implementation and required verification ready for review |
| Done | Changes reached `master` and acceptance criteria are met; verification-only work completes on its recorded outcome |
| Canceled | Will not be done |
| Duplicate | Merged into another issue, which is linked |

Readiness labels are separate from state: see [triage labels](triage-labels.md).

## Dependencies

Record blocking relations explicitly. Start dependent implementation only when its
prerequisite is implemented and verified on the branch used as its base; merge order
still follows the dependency. A canceled prerequisite requires replanning or removing the
dependent work, never bypassing it.

## Parent and sub-issues

Similar work is one parent issue per family with one sub-issue per model or unit; variants
are checkboxes inside the sub-issue. The parent holds the shared checklist once. A parent
is Done when every sub-issue is Done or waived by the user. Parenthood is not a blocker,
so blocking relations stay explicit. A ticket merged into another is marked Duplicate of
the kept one.

## Evidence

Evidence lives only in the issue and its PR: source and environment identities, commands,
checks and outcomes, exclusions, reuse reasons and remaining limitations. The repository
holds no evidence files.

## PR grouping and delivery

Default to one branch and PR per cohesive feature, including several issues when
appropriate. Link every included issue, map its acceptance criteria to implementation and
evidence, and keep it open until the PR merges. Use stacked PRs when separate review units
or dependency sequencing help delivery; record the grouping in the issue before
implementation. Routine grouping needs no approval.

Push task-owned branches to the existing SSH remote. PRs are squash-merged; write the PR
title as a Conventional Commit header, because it becomes the squash commit's header
(see [releases](../development.md#releases) for how the release is decided). There is no
CI check job; do not assume branch protection or Linear automation.

For stacks, the first PR targets `master` and each descendant targets its parent branch.
Link parent PRs and the merge order. Review incremental diffs and verify the cumulative
delta against `master`, recording base and head SHAs. Draft PRs may hold incomplete work.

Humans merge stacks bottom-up. After each merge, retarget or restack the remaining
branches, inspect the resulting diffs, reassess evidence applicability, and repeat
affected checks and review. Use `--force-with-lease` only to rewrite task-owned branches.
