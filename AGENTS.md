# clearml-yolo agent instructions

`clearml-yolo` (CY) provides Hydra/hydra-zen applications for training, prediction,
validation, metrics, reports, comparison and export across several detector families,
with ClearML publication. The [README](README.md) describes usage.

## Rules

- Deliver every change through a Linear issue in project `clearml-yolo`, a task branch and
  a GitHub PR. Agents commit, push task branches and open PRs; humans merge, and a merge to
  `master` releases automatically. Never push to or merge into `master`. Explicit
  no-commit or no-push limits and the active host mode take precedence.
- Stage only task-owned paths or hunks. Never stash, reset or revert other work, or bypass
  hooks to hide a failure. Preserve ignored local configuration.
- Preserve pre-existing services, containers and data. Track and clean up only resources
  the task created; touch a shared resource only with ownership evidence and user
  authorization.
- Use Conventional Commits. The commit type decides the release: `feat`, `fix` and `perf`
  bump the version, and so does any type marked breaking (`!` or a `BREAKING CHANGE:`
  footer); other types do not.
- Keep `digital-metrics` pinned to the approved upstream revision. Change its source,
  checkout, dependency reference or locked revision only on explicit user intent; adapt
  this project's integration and report upstream issues instead of patching the dependency.
- Never commit `[tool.uv.sources]`.
- Code releases are Git commits and annotated tags only. Build project wheels and source
  archives only for a concrete debugging task, never as deliverables or routine checks;
  this overrides generic distribution-build guidance in shared skills. Independently
  versioned `weights-*` GitHub Releases are the one exception, and only when the user
  explicitly asks for one.
- Mocked tests do not establish native, GPU or upload outcomes.
- Report each required check as passed, failed, deferred, waived or error. A deferred
  required check blocks acceptance and merge readiness; only the user waives a check.
- Behavior, interface, dependency, security and operational-policy changes get a fresh
  independent review after integrated verification; wording edits may be self-reviewed.
- Tests exercise product code, never project tooling.
- Pass ClearML project names and tags explicitly; application configuration must not
  depend on an agent harness or machine.
- `README.md` is Russian and user-facing; other documentation, skills and instructions are
  English.
- Documentation states current behavior only. Observations (counts, timings, results,
  dates) go to the Linear issue or PR. Do not add a documentation checker.
- Adding, renaming or removing a `docs/feature/` file updates its README section in the
  same change; a README section states nothing its feature file does not.
- When rewriting behavior documentation, compare the original behavior, conditions and
  exceptions with their new homes, separate policy changes from wording changes, and have
  the reviewer compare meaning against the original rather than judge length or wording.
- Preserve the selected parent model/effort and host planning restrictions when delegating.

## Read when relevant

| Trigger | Read |
| --- | --- |
| Change application behavior or configuration | The affected [`docs/feature/`](docs/feature/) file |
| Change imports, module structure or lint policy | [Architecture](docs/architecture.md) |
| Set up dependencies, verify, commit, pair or release | [Development procedures](docs/development.md); read its commit procedure before every commit |
| Plan or deliver tickets and PRs | [Issue tracker](docs/agents/issue-tracker.md) and [issue template](docs/agents/issue-template.md) |
| Select checks, report verification | [verification-workflow](.agents/skills/verification-workflow/SKILL.md) |
| Run live tests or native observations, manage a test environment | [running-integration-tests](.agents/skills/running-integration-tests/SKILL.md) |
| Triage mutation survivors or change mutation selection | [mutation-testing](.agents/skills/mutation-testing/SKILL.md) |
| Prepare merge readiness, inspect or recover a release | [release](.agents/skills/release/SKILL.md) |

`scripts/session_status.sh` runs at Claude and Codex session start and reports the branch,
uncommitted paths, other worktrees, unmerged branches and a recorded test environment.
Changes it lists may belong to another session.

## Instruction files

`AGENTS.md` is the shared instruction source; `CLAUDE.md` stays a regular file containing
`@AGENTS.md`. Author project skills in `.agents/skills/`; `.claude/skills` is a symlink to it.

## Agent skills

### Issue tracker

For ticket operations, use the [Linear conventions](docs/agents/issue-tracker.md).

### Triage labels

For ticket triage, use the [readiness labels](docs/agents/triage-labels.md).

### Domain docs

Before domain exploration, follow the [domain documentation guidance](docs/agents/domain.md).
