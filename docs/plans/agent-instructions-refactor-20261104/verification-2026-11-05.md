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

As of 2026-11-05:

- `uv run --frozen --no-sync python scripts/verify.py --docs` and
  `uv run --frozen --no-sync pytest tests/test_check_docs.py -q` need a provisioned
  worktree environment.
- Commit hooks (`pre-commit`, `changelog`, `verify --hook`) run at commit time.
- Paired CY/queue release check before delivery.
- Fresh-session skill discovery in Claude and Codex.
- Fresh independent review.

### Update 2026-11-07

Status of each 2026-11-05 item above:

- `verify.py --docs` and `pytest tests/test_check_docs.py`: `scripts/verify.py` no longer
  exists on the current `master`, so `scripts/check_docs.py --all` was run as a substitute,
  together with `pytest tests/test_check_docs.py -q`, on 2026-11-07 (see
  [review-2026-11-07.md](review-2026-11-07.md)).
- Commit hooks: committed as `43de5af`, released in v0.46.0 (`git tag --contains 43de5af`).
  Hook execution for that commit is not independently evidenced; its CHANGELOG entry was
  added by a later changelog hook run.
- Paired CY/queue release check: credited to v0.46.0 by the remaining-work plan; not
  re-verified here.
- Fresh-session skill discovery in Claude and Codex: pending (remaining-work T6.2, owner);
  done later the same day, see the next section.
- Fresh independent review: done in [review-2026-11-07.md](review-2026-11-07.md), pass with
  one minor rule narrowing.

### Update 2026-11-07: fresh-session skill discovery

Remaining-work T6.2. Each host ran once, non-interactively, from the repository root of
the primary `master` checkout at `255c69c`:

- Claude: `claude -p "List the names of the project skills available to you in this
  repository, one per line, nothing else." --max-turns 1` exited 1 with
  `Error: Reached max turns (1)` and no answer, which suggests the session attempted a
  tool call. The rerun with the prompt prefixed by "Without using any tools," and the
  same `--max-turns 1` exited 0.
- Codex: `codex exec "List the names of the project skills available to you in this
  repository, one per line, nothing else."` exited 0 without running any command.

Both answers listed the same 19 names, which equal the directories in `.agents/skills/`
and the `.claude/skills/` links: `running-end-to-end-tests`, `speckit-analyze`,
`speckit-assess-decide`, `speckit-assess-define`, `speckit-assess-intake`,
`speckit-assess-research`, `speckit-assess-shape`, `speckit-bug-assess`,
`speckit-bug-fix`, `speckit-bug-test`, `speckit-checklist`, `speckit-clarify`,
`speckit-constitution`, `speckit-converge`, `speckit-implement`, `speckit-plan`,
`speckit-specify`, `speckit-tasks` and `speckit-taskstoissues`. `AGENTS.md` and
`CLAUDE.md` name only `running-end-to-end-tests`, so the full list came from each host's
skill discovery. Fresh-session discovery passes in both hosts.
