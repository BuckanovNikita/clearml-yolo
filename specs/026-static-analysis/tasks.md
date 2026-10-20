# Tasks: static analysis policy audit

## Phase 1 — Setup and evidence

- [x] T001 Inspect pyproject.toml, .pre-commit-config.yaml and existing staged work.
- [x] T002 [P] Audit explicit Ruff/mypy suppressions in pyproject.toml and src/ (read-only delegate).
- [x] T003 [P] Audit all unselected Ruff catalog rules against pyproject.toml (read-only delegate).

## Phase 2 — US1: revised policy

- [x] T004 [US1] Tighten justified Ruff/mypy settings in pyproject.toml and make minimal compatible source corrections.
- [x] T005 [US1] Verify repository-wide Ruff/mypy and capture rule dispositions in docs/static-analysis.md.

## Phase 3 — US2: dead-code gate

- [x] T006 [US2] Add Vulture to pyproject.toml, uv.lock and .pre-commit-config.yaml without unrelated resolution changes.
- [x] T007 [US2] Make intentional unused callback/fixture parameters explicit in affected src/ and tests/ files.
- [x] T008 [US2] Verify the configured Vulture hook, negative control and affected regression tests.

## Phase 4 — Documentation update and acceptance

- [x] T009 Update docs/development.md and docs/static-analysis.md; validate Markdown, links and examples.
- [x] T010 Record parent verification and fresh independent review in verification-2026-10-12.md.

## Dependencies and parallel work

T002 and T003 run independently while the parent probes Vulture and owns all writes.
T004 follows both audits. T006/T007 follow the Vulture probe, then T008 verifies them.
T009 follows final policy integration; T010 follows all checks. US1 and US2 share
pyproject.toml, so the parent serializes their edits. No delegated agent owns writes.

## Phase 5 — Approved follow-up and landing (2026-10-13)

- [x] T011 Reconcile prior task changes, append plan and validate architecture planning.
- [x] T012 Enable explicit Ruff preview codes and preserve the existing lock while adding exact stubs.
- [x] T013 [P] Fix encodings, comparison names and ClearML keyword-only verification; verify affected paths.
- [x] T014 [P] Remove SciPy/tqdm overrides and correct types without weakening strictness.
- [x] T015 Add scoped executable tooling boundary contracts and negative cases.
- [x] T016 Run static checks, negative controls, architecture checks, full tests and hooks.
- [x] T017 Update policy/report inventory and dated evidence; validate documentation.
- [x] T018 Obtain fresh independent review, reconcile diff and validate architecture acceptance.
- [x] T019 Commit task-owned changes, land on master and finish the established Git-tag-only release.

T013 can run alongside parent T012/T015; T014 depends on installed stubs from T012.
T016 depends on their integration. T017/T018 follow verification; T019 follows acceptance.

## Phase 6 — Configuration simplification (2026-10-19)

- [x] T020 Append FR-006–008, plan and config-split/architecture.json; validate planning and artifact consistency.
- [x] T021 [US1] Extract Ruff and import-linter configuration from pyproject.toml; preserve normalized contracts and use ALL with explained exclusions.
- [x] T022 [US1] Adapt tests/test_architecture.py and .pre-commit-config.yaml to native configuration discovery, including negative controls.
- [x] T023 Verify static gates, architecture/tooling tests, configuration equivalence and applicable hooks.
- [x] T024 Update docs/static-analysis.md, docs/development.md, docs/agent-workflow.md and current architecture pointers; validate Markdown and links.
- [x] T025 Record dated results, fresh independent review and diff reconciliation; validate architecture acceptance.
- [ ] T026 Commit task-owned changes and evaluate native release within existing dirty-tree safeguards.

T020 precedes edits; T021 precedes T022/T023; T024 follows the final configuration.
T025 follows verification and documentation; T026 follows acceptance. Shared configuration
edits stay with the parent; the independent reviewer has no write ownership.

T026 is deferred by the native dirty-tree safeguard; see [dated evidence](config-split/verification.md).
Implementation acceptance passed; no commit, version tag or push is claimed.
