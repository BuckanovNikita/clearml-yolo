# clearml-yolo agent instructions

`clearml-yolo` (CY) supports Python `>=3.12.13,<3.14` and provides Hydra/hydra-zen
applications for native Ultralytics YOLO training, prediction, validation, metrics,
reports and comparison. Pass ClearML project names and tags explicitly; application
configuration must not depend on an agent harness or machine.

## Commands

Authoritative details and prerequisites: [development procedures](docs/development.md#verification).

```bash
uv sync --frozen --dev                                     # after populating external/ (docs/development.md#external-dependencies)
uv run --frozen --no-sync python scripts/local_release.py --install-hooks  # prek hooks
uv run --frozen --no-sync prek run --all-files                # Ruff, mypy, Vulture, import-linter, cached pytest, docs
uv run --frozen --no-sync pytest --testmon-noselect           # complete suite: acceptance, refreshes testmon
uv run --frozen --no-sync python scripts/check_docs.py --all  # Markdown and local-link validation
```

## Read when relevant

Read the linked guidance when the task matches its trigger; do not load every reference
for every task. Read guidance instead of copying shared skills into the repository.

| Task | Required guidance |
| --- | --- |
| Change application behavior or configuration | [Project contract summary](docs/project-contracts.md), then affected topics in the [current contract index](docs/current-contracts.md) and their implementation evidence |
| Set up dependencies, verify code or commit | Relevant sections of [development procedures](docs/development.md); read the commit procedure before every commit |
| Plan, implement, fix, resume or accept repository changes | Shared `python-project-workflow` and `module-architecture-planning` skills, with the [architecture gate](docs/agent-workflow.md#mandatory-module-architecture-planning-and-acceptance) |
| Run any Spec Kit stage, including planning or bug-source capture | [Agent workflow policy](docs/agent-workflow.md), then the applicable installed skills |
| Verify native execution, training, GPU use or ClearML publication | [running-end-to-end-tests](.agents/skills/running-end-to-end-tests/SKILL.md); load the project-local [clearml-yolo-environment](.agents/skills/clearml-yolo-environment/SKILL.md) for this machine |
| Change contracts or their documentation | [Current contract index](docs/current-contracts.md#maintaining-consistency) and the [documentation stage](docs/agent-workflow.md#mandatory-documentation-stage), including the portable `clearml-yolo` usage skill ([maintenance](docs/agent-workflow.md#portable-usage-skill-maintenance)) |

## Workflow and completion

- The [constitution](.specify/memory/constitution.md) defines typed Python, effect
  ownership, verification, preservation and collaboration rules. The
  [workflow policy](docs/agent-workflow.md) owns task routing, authorization boundaries,
  architecture acceptance and documentation stages. Read the policy before workflow
  operations so its safeguards apply in time.
- Use `python-project-workflow` for Python repository work. Apply its compatibility,
  architecture, verification and release requirements within this project's Spec Kit
  routes; the native workflow owns stage order, task artifacts and review sequence.
- If a required skill is unavailable, report the missing gate and continue independent
  inspection without claiming acceptance.
- Inspect current implementation and existing changes; plans are intent, and executed
  checks are evidence.
- Start new work from the [stage-zero specification](specs/000-baseline/spec.md). It
  identifies the current contracts and immutable pre-reset history. New features use the
  new numbering epoch beginning at `001`; do not reactivate retired task ledgers.
- Automatically route completion requests through the applicable Spec Kit workflow in
  [agent-workflow.md](docs/agent-workflow.md#automatic-workflow-routing), reusing existing
  artifacts and preserving completed history. Keep the process proportionate and honor
  explicitly limited requests; continue authorized stages without asking the user to
  invoke each skill.
- Reconcile the actual task-owned diff with the ledger, checks and review before
  acceptance; then evaluate the native release workflow within authorization.
  Documentation-only changes may produce no new version. Missing or failed required
  checks remain acceptance gaps.
- Complete the mandatory documentation stage before reporting implementation or bug-fix
  completion: update affected guidance and validate Markdown, local links and changed
  examples, or record the reviewed scope and a concrete no-change reason. Missing
  required updates or failed validation blocks completion. Documentation-only work needs
  documentation checks.
- Mocked tests do not establish native/GPU/upload outcomes.

## Collaboration and review

- Use `sol-orchestration` and native subagents when independent work or review is
  useful; trivial low-risk edits need proportionate checks, not manufactured parallel work.
- Give bounded agents exclusive write ownership and no further delegation. The parent
  integrates and verifies; substantive changes require fresh independent review afterward.
- Report unavailable required review as an acceptance gap. Preserve the selected parent
  model/effort and respect live tool/concurrency limits and planning restrictions.

## Dependencies, commits and releases

- Code releases consist only of Git commits and annotated version tags. Independently
  versioned `weights-*` GitHub Releases may contain the project's verified model asset
  tar archives, manifests, checksums and upstream notices under the explicit
  model-assets exception; follow [weight releases](docs/development.md#model-weight-releases).
  Code-release hooks do not publish these assets.
- Build project `.whl` wheels and `.tar.gz` source archives only for a concrete
  debugging task; never build or present them as release deliverables or routine release
  checks. This project rule overrides generic distribution-build guidance in shared skills.
- Keep `digital-metrics` pinned to the approved upstream revision. Do not change its
  source, checkout, dependency reference or locked revision without explicit user intent;
  general cleanup or dependency maintenance does not authorize this. Adapt this project's
  integration; report upstream issues rather than patching or monkeypatching the dependency.
- Before releasing or delivering either CY or cy-queue, verify the latest source versions
  of both together, including the proposed release versions. Follow the
  [paired release check](docs/development.md#paired-cy-and-queue-release-check): normal
  dependency resolution, matching source/installed metadata and the queue integration
  suite are mandatory. Incompatible or unavailable evidence blocks delivery.
- Use Conventional Commits and complete the native release workflow when user or standing
  authorization covers delivery; explicit no-commit/no-release limits and the active host
  mode take precedence. Stage only task-owned paths or hunks and preserve unrelated staged
  and unstaged changes. Do not stash, reset, revert or bypass hooks to make a check pass.
- Before each commit, follow the [commit procedure](docs/development.md#commit-procedure):
  temporarily remove the entire local `[tool.uv.sources]` section, preserve it exactly,
  and restore it unstaged after commit/hooks finish, including failed attempts.

## Documentation

- Write `README.md` in Russian for users, with installation, usage, configuration and
  troubleshooting; keep agent workflow policy elsewhere. Write other documentation,
  skills and instructions in English unless required otherwise.
- Keep observed counts, timings and deployment status in dated evidence. Keep artifact
  inventories in maintained publication contracts rather than copying counts into
  instructions.

## Instruction files and installed tooling

- `AGENTS.md` is the shared instruction source; keep `CLAUDE.md` a regular file
  importing it with `@AGENTS.md`.
- Author project skills in `.agents/skills/`; `.claude/skills` is a symlink to it for
  Claude discovery.
- Keep installed Spec Kit skills, commands, templates and `.specify/` files unchanged
  unless explicitly requested. Project workflow policy belongs in linked project guidance
  or separate project hooks; feature specifications under `specs/` are project documentation.
