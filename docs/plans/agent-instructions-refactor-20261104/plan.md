# Agent instruction and project skill refactor

## Approved outcome

Restructure `AGENTS.md` and the authored `running-end-to-end-tests` skill for current
instruction and skill best practices without changing any normative rule: a command block
near the top, bulleted workflow rules, one closing section for instruction-file rules, a
third-person skill description with trigger terms, labelled checklist steps, and
progressive disclosure for multi-model acceptance. `CLAUDE.md` stays a regular file
importing `@AGENTS.md`; `.claude/skills` stays a symlink to `.agents/skills`. Generated
Spec Kit skills and `.specify/` are unchanged.

## Architecture

[architecture.json](architecture.json) records inspected documentation-only impact.
No product modules, import boundaries or runtime effects change. Existing documentation
validators and architecture checks remain unchanged.

## Tasks and dependencies

- [x] Inspect instructions, the authored skill and its reference, linked workflow
  documentation, inbound path pins and generated Spec Kit manifests.
- [x] Validate the architecture planning record before editing.
- [x] Rewrite `AGENTS.md` with every rule kept, moved or merged.
- [x] Restructure the skill, keep its name and path, and move multi-model acceptance to
  `references/multi-model-acceptance.md`.
- [x] Add a table of contents and topic headings to `references/pipeline-prerequisites.md`
  without changing its text.
- [x] Run the available documentation, frontmatter, size, adapter and preservation checks;
  record dated results.
- [ ] Coordinating parent obtains fresh independent review after verification.
- [ ] Commit with hooks in a provisioned worktree and evaluate the native release workflow
  (documentation-only; no version expected) after the paired CY/queue check.

The skill edits depend on the planning check. Parent integration and final verification
precede independent review and commit.

## Acceptance

Every rule from the previous `AGENTS.md`, skill and reference survives, including the
skill's narrower wheel/source-archive rule (packaging/install investigation only), which is
not an exact duplicate of the `AGENTS.md` rule. Step 7 failure checks and Step 5 report-count
checks follow the base `origin/master` `66279a6` (0.45.1) pipeline outcome and training-count
contracts. Relevant links and anchors resolve, the skill
frontmatter parses and stays portable, and entrypoints stay within size budgets. File
inspection establishes structure only; fresh-session skill discovery in each host is
verified separately and must not be claimed from file checks. This task does not modify
application behavior.
