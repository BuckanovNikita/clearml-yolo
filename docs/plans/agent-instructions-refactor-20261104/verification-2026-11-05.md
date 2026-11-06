# Verification — 2026-11-05

Worktree on branch `refactor/agent-instructions-20261104`, base `origin/master` at
`66279a6` (version 0.45.1; the checks below first ran on `8be76e4`, 0.45.0, and were
rerun or reconciled after the fast-forward as recorded under Review fixes). Read-only checks used the original checkout's virtual
environment with `python -I -B`; the worktree has no `.venv` or `external/` yet.

## Passed

| Check | Result |
| --- | --- |
| Architecture record, `--phase plan` before editing | exit 0 |
| `scripts/check_docs.py --root . --all` plus the new untracked Markdown files | 239 files, 0 issues |
| Skill frontmatter with `yaml.safe_load`: `name` matches the directory, portable keys only | pass; description 464 characters |
| Size budget | `AGENTS.md` 119 lines (8272 bytes), `SKILL.md` 295 lines after review fixes, references 207 and 39 lines |
| `CLAUDE.md` is `@AGENTS.md`; `.claude/skills` links to `../.agents/skills` | pass |
| No diff under `.specify/` or `.agents/skills/speckit-*` | pass |
| Every backticked identifier from the previous three files still present | pass (none missing) |
| Word-level diff of previous skill and reference text against the new files | only the planned replacements: description, contents lists, terms line, mode paragraph, static-check command, release-policy sentence, multi-model pointer and moved-file link prefix |
| `git diff --check` | clean |
| Architecture record, `--phase acceptance` | exit 0 |

## Review fixes

After the base moved to `66279a6`, review fixes changed `SKILL.md`: Contents labels now
match the step headings; Step 7 failure checks follow the 0.45.1 pipeline outcome policy
(strict standalone and `skip_train=true` runs, interruptions and training failures always
fatal, warning completion with `pipeline_outcome` evidence after verified training); Step 5
checks unavailable training counts; and the packaging/install-only wheel and source-archive
rule is restored. Rerun on the new base: `scripts/check_docs.py --root . --all` (244 files,
0 issues), frontmatter parse (portable keys, description 464 characters) and
`git diff --check` (clean).

## Documentation stage

Reviewed scope: inbound references to the skill and its reference in
`tests/test_check_docs.py`, `docs/development.md`, `docs/current-contracts.md`,
`specs/000-baseline/spec.md`, `.specify/memory/constitution.md` and earlier architecture
records, plus `docs/agent-workflow.md`. No change needed: they pin only the unchanged skill
and reference paths or the skill name, and their descriptions of the skill (portable
native acceptance, readback, comparison and cleanup) remain accurate. The
documentation-only evidence that `docs/agent-workflow.md` requires (intent, tasks,
no-impact architecture, dated checks) is in this directory.

## Pending

Updated 2026-11-07:

- Fresh independent review: done, pass, in [review-2026-11-07.md](review-2026-11-07.md).
- Commit with hooks: done as `43de5af`, released in v0.46.0. `scripts/verify.py` no longer
  exists on the current `master`; `scripts/check_docs.py --all` and
  `pytest tests/test_check_docs.py` were rerun on 2026-11-07 (see the review).
- Paired CY/queue release check: delivered with v0.46.0 (recorded in the remaining-work
  plan, not re-verified here).
- Fresh-session skill discovery in Claude and Codex (remaining-work T6.2, owner): pending.
