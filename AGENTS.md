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
uv run --frozen --no-sync pytest --testmon-noselect           # complete suite: acceptance, refreshes testmon
```

## Read when relevant

Read the linked guidance when the task matches its trigger; do not load every reference
for every task. Read guidance instead of copying shared skills into the repository.

| Task | Required guidance |
| --- | --- |
| Change application behavior or configuration | [Project contract summary](docs/project-contracts.md), then affected topics in the [current contract index](docs/current-contracts.md) and their implementation evidence |
| Set up dependencies, verify code or commit | Relevant sections of [development procedures](docs/development.md); read the commit procedure before every commit |
| Plan, implement, fix, resume or accept repository changes | [Workflow policy](docs/agent-workflow.md), including its [module boundaries](docs/agent-workflow.md#module-boundaries) |
| Run any Spec Kit stage, including planning or bug-source capture | [Agent workflow policy](docs/agent-workflow.md), then the applicable installed skills |
| Verify native execution, training, GPU use or ClearML publication | [running-end-to-end-tests](.agents/skills/running-end-to-end-tests/SKILL.md); load the project-local [clearml-yolo-environment](.agents/skills/clearml-yolo-environment/SKILL.md) for this machine |
| Change contracts or their documentation | [Current contract index](docs/current-contracts.md#maintaining-consistency) and the [documentation guidance](docs/agent-workflow.md#documentation) |

## Workflow and completion

- Preserve the selected parent model/effort and host planning restrictions.

- The [constitution](.specify/memory/constitution.md) defines typed Python, effect
  ownership, verification, preservation and collaboration rules. The
  [workflow policy](docs/agent-workflow.md) owns task routing, authorization boundaries,
  verification and documentation guidance. Read the policy before workflow
  operations so its safeguards apply in time.
- For Python repository work, preserve the declared Python compatibility, check
  affected module boundaries, run the project verification gates and follow authorized
  release procedures. The native Spec Kit workflow owns stage order, task artifacts and review
  sequence.
- Start from the [product specification](specs/000-baseline/spec.md) and its
  technical contracts. New behavior changes use the native Spec Kit workflow;
  product specifications describe requirements without implementation status.
- Reconcile the actual task-owned diff with the ledger, checks and review before
  acceptance; then evaluate the native release workflow within authorization.
  Documentation-only changes may produce no new version. Missing or failed required
  checks remain acceptance gaps.
- Mocked tests do not establish native/GPU/upload outcomes.

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
  mode take precedence. Preserve unrelated changes and stage only task-owned hunks;
  do not stash, reset or revert unrelated work, or bypass hooks to hide failures.
- Follow the [commit procedure](docs/development.md#commit-procedure) for coherent split
  commits, targeted intermediate skips and final verification of committed inputs.
  Preserve local source overrides; validate them only at final acceptance.

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

## Project execution policy

Use Spec Kit for new capabilities or documented behavior changes; routine fixes,
docs and small refactors proceed directly, updating existing task artifacts as needed.
Behavior, interface, dependency, security and operational-policy changes require
independent review after integration and verification; wording edits may be self-reviewed.
Documentation checks are limited to native Spec Kit or OpenSpec checks. Local commits
may be autonomous; pushes require separate authorization, including existing session authorization.

## Specification rewrites

Compare the original behavior, conditions and exceptions with their new authoritative
homes, including requirements embedded in scenarios. Separate approved policy changes
from wording changes; resolve overloaded terms before editing. Retain compatibility
obligations, remove historical status claims, and have the reviewer compare meaning
against the original source rather than judge length or wording alone.
