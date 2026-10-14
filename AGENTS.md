# clearml-yolo agent instructions

`clearml-yolo` is a Python 3.12 group of Hydra/hydra-zen applications for native
Ultralytics YOLO training, prediction, validation, metrics, reports and comparison.
`AGENTS.md` is the shared instruction source; keep `CLAUDE.md` a relative symlink to it.

Use the shared `python-project-workflow` skill for Python repository work. Apply its
compatibility, architecture, verification and release requirements within this project's
Spec Kit routes; the native workflow owns stage order, task artifacts and review sequence.
Read the relevant guidance below instead of copying shared skills into the repository.
If a required skill is unavailable, report the missing gate and continue independent
inspection without claiming acceptance.

## Working agreement

- Carry authorized work through implementation, appropriate verification and documentation.
  Inspect relevant code, configuration and existing changes first; preserve unrelated work.
  Plans describe intent; the repository and dated checks establish implementation evidence.
- Respect the active host mode and existing authorization. Planning-only work permits
  inspection, not writes or mutating hooks. Existing user or standing authorization can
  cover commits and native release delivery; skills and tasks do not create authorization
  for deployment, dependency updates or unrelated repairs. Explicit stopping points take
  precedence. Ask only for material missing information or a new scope decision.
- For bugs, capture and reproduce the failure when feasible, then verify the original
  failure path. Report checks and limitations accurately.
- Follow the existing Python toolchain. Prefer strict types, explicit access, Loguru and
  Pydantic; handle specific exceptions at a boundary that can report or resolve them.
  Keep code comments and log messages in English.
- Track and clean up resources created by the task; preserve pre-existing shared services,
  containers and data. Keep machine-specific knowledge in global environment guidance.

## Collaboration

Use `$sol-orchestration` and native subagents when useful independent work or review
justifies them. Plans identify ownership, dependencies, acceptance evidence and useful
parallel work within the selected workflow's stage and role rules. Trivial low-risk edits
may proceed directly with proportionate checks; do not manufacture parallel tasks.
Bounded subagents must not delegate further. The primary agent inspects the combined
diff and owns final verification. Substantive changes require fresh independent review
after integration and checks; use that final review for Python and architecture acceptance
as well. Smaller changes use review when risk or uncertainty warrants it. Respect live
tool/model/concurrency limits and planning restrictions. If required delegation or review
is unavailable, report the acceptance gap and continue independent safe work.

## Read when relevant

Read the linked guidance when the task matches its trigger; do not load every reference
for every task.

| Task | Required guidance |
| --- | --- |
| Change application behavior or configuration | [Project contract summary](docs/project-contracts.md), then affected topics in the [current contract index](docs/current-contracts.md) and their implementation evidence |
| Set up dependencies, verify code or commit | Relevant sections of [development procedures](docs/development.md); read the commit procedure before every commit |
| Plan, implement, fix, resume or accept repository changes | Shared `python-project-workflow` and `module-architecture-planning` skills, with the [architecture gate](docs/agent-workflow.md#mandatory-module-architecture-planning-and-acceptance) |
| Run any Spec Kit stage, including planning or bug-source capture | [Agent workflow policy](docs/agent-workflow.md), then the applicable installed skills |
| Verify native execution, training, GPU use or ClearML publication | [running-end-to-end-tests](.agents/skills/running-end-to-end-tests/SKILL.md); load `clearml-yolo-environment` when available for this machine |
| Change contracts or their documentation | [Current contract index](docs/current-contracts.md#maintaining-consistency) and the [documentation stage](docs/agent-workflow.md#mandatory-documentation-stage), including the portable usage skill |

## Dependencies and Git

- Keep `digital-metrics` pinned to the approved upstream revision. Do not change its
  source, checkout, dependency reference or locked revision without explicit user intent.
  General cleanup or dependency maintenance does not authorize this. Adapt this project's
  integration; report upstream issues rather than patching or monkeypatching the dependency.
- Use Conventional Commits and complete the native release workflow when user or standing
  authorization covers delivery. Explicit no-commit/no-release limits and the active host
  mode take precedence. Stage only task-owned paths or hunks; preserve unrelated staged
  and unstaged changes. Do not stash, reset, revert or bypass hooks to make a check pass.
- Before each commit, follow the [commit procedure](docs/development.md#commit-procedure):
  temporarily remove the entire local `[tool.uv.sources]` section, preserve it exactly,
  and restore it unstaged after commit/hooks finish, including failed attempts.
- Keep installed Spec Kit skills, commands, templates and `.specify/` files unchanged
  unless explicitly requested. Project workflow policy belongs in linked project guidance
  or separate project hooks; feature specifications under `specs/` are project documentation.

## Workflow and completion

Automatically route completion requests through the applicable Spec Kit workflow in
[agent-workflow.md](docs/agent-workflow.md#automatic-workflow-routing), reusing existing
artifacts and preserving completed history. Keep the process proportionate and honor
explicitly limited requests; continue authorized stages without asking the user to invoke
each skill. Read the policy before workflow operations so its safeguards apply in time.
Reconcile the actual task-owned diff with the ledger, checks and review before acceptance;
then evaluate the native release workflow within authorization. Documentation-only changes
may produce no new version. Missing or failed required checks remain acceptance gaps.

Complete the mandatory documentation stage before reporting implementation or bug-fix
completion: update affected guidance and validate Markdown, local links and changed
examples, or record the reviewed scope and a concrete no-change reason. Missing required
updates or failed validation blocks completion. Documentation-only work needs documentation
checks. Mocked tests do not establish native/GPU/upload outcomes.

Write `README.md` in Russian for users, with installation, usage, configuration and
troubleshooting; keep agent workflow policy elsewhere. Write other documentation, skills
and instructions in English unless required otherwise. Keep observed counts, timings and
deployment status in dated evidence. Keep artifact inventories in maintained publication
contracts rather than copying counts into instructions. Pass ClearML project names and
tags explicitly; application configuration must not depend on an agent harness or machine.
