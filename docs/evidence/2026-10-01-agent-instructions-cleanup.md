# Agent instructions cleanup

**Date**: 2026-10-01
**Scope**: shared agent instructions and on-demand documentation only.

## Intent and plan

The user requested one shared instruction source, `CLAUDE.md` as a symlink to
`AGENTS.md`, and less guidance loaded on every task. Inspection found that the tracked
relative symlink already had the requested target. Preserve it and reduce `AGENTS.md`
to working rules, mutation boundaries and explicit task-based reading routes.

This is a bounded instruction/documentation refactor, not an application feature or
bug fix. Reuse the findings of the [prior audit](2026-09-30-instruction-contract-audit.md)
without rewriting its dated record. No installed Spec Kit tooling or active feature
artifacts require changes. No extension hooks are registered in `.specify/extensions.yml`.

Move detailed product requirements to [project contracts](../project-contracts.md),
verification/dependency/commit procedures to [development](../development.md), and
Spec Kit routing/documentation/safeguards to [workflow policy](../agent-workflow.md).
Use ordinary documentation because these are references for existing workflows;
reuse the existing orchestration and end-to-end skills rather than adding competing skills.

## Task ledger

- [x] T001 Inspect instruction files, symlink modes, current changes, existing skills and
  inbound links; obtain an independent read-only inventory.
- [x] T002 Preserve the existing `CLAUDE.md -> AGENTS.md` symlink and move detailed
  requirements into the three on-demand guides.
- [x] T003 Rewrite `AGENTS.md` as the always-loaded rules and reading router.

### Documentation update and validation (depends on T002 and T003)

- [x] T004 Update `docs/current-contracts.md` to route the relocated summary and workflow
  policy; preserve historical evidence and completed task history.
- [x] T005 Validate changed Markdown, all first-party local links/anchors and the symlink;
  verify preservation of installed tooling, dependencies and existing local changes.
- [x] T006 Inspect the combined diff and obtain independent read-only acceptance review;
  record actual results and limitations below.

## Documentation scope

Affected: `AGENTS.md`, this evidence record, the three linked guides and
`docs/current-contracts.md`. The product-contract block and detailed Spec Kit policy
are relocated with their requirements intact. The commit section retains its exact
example and failure/restoration rules.

README, active product specs, quickstarts, migrations, integration skills and global
environment examples were reviewed for scope: command syntax, runtime behavior,
configuration and execution guidance do not change, so they need no edits. Existing
references to reading `AGENTS.md` remain valid through its new task-based routes.

## Verification and limitations

- `AGENTS.md` decreased from 268 lines / 2,176 whitespace-delimited words / 16,549 bytes
  to 81 lines / 712 words / 5,596 bytes. This measures the root file, not host prompt
  tokens or the total documentation size; host behavior determines which files are loaded.
- Parsed 193 first-party Markdown paths and checked 343 local links/anchors. All six
  changed Markdown files passed fence, heading-spacing, final-newline and whitespace
  checks; all 70 local links in those files passed. `git diff --check` passed.
- The repository-wide scan found one existing broken link in `.specify/memory/constitution.md`
  to `tests/test_ultralytics_params.py`. The constitution is byte-identical to HEAD and
  the target is also absent at HEAD. No new link failures were introduced; the protected
  installed file remains unchanged. The whole repository link scan is not fully passing.
- Product contracts, detailed workflow policy (with its relative link adjusted) and the
  commit procedure were checked against their original text in `HEAD:AGENTS.md`.
- `CLAUDE.md` remains a relative symlink to `AGENTS.md`, resolves to identical content
  and retains its tracked `120000` mode. All 68 captured protected file hashes were
  unchanged, including installed Spec Kit files, `uv.lock` and the initially dirty
  `pyproject.toml`; no application or external dependency changes were made.
- The independent inventory review completed without writes. After the parent inspected
  the diff and validated documentation, a fresh read-only acceptance reviewer returned
  `ship` with no findings, confirming preserved requirements, explicit reading triggers,
  valid relocated links and unchanged protected files. The parent reran final documentation
  and preservation checks after recording acceptance. Requested reviewer settings were
  `gpt-5.6-sol` / `medium`; observed runtime model/effort and token usage were unavailable.

No application execution, native training, GPU, ClearML publication, commit, release
or deployment is part of this change. Existing external links were not fetched;
local-link validation does not establish remote service availability.
