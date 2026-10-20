# Tasks: Git workspace startup warning

## Phase 1: Setup and architecture

- [x] T001 Capture confirmed behavior and baseline references in spec.md and checklists/requirements.md.
- [x] T002 Record implementation decisions, contracts and ownership in plan.md, research.md, data-model.md, contracts/startup.md and architecture.json; validate the planning record.
- [x] T003 Analyze spec/plan/tasks coverage before implementation; preserve the read-only analysis outcome in verification.md.

## Phase 2: US1 — Notice unversioned configuration

Independent acceptance: actual command help/config launches warn once outside Git
and stay quiet within a working tree; inert multirun continues through both jobs.

- [x] T004 [US1] Add behavior and CLI regression tests in tests/test_git_workspace.py and observe the missing-warning failure.
- [x] T005 [US1] Implement the Git adapter in src/clearml_yolo/adapters/runtime/git_workspace.py and wire src/clearml_yolo/entrypoints/hydra/common.py.
- [x] T006 [US1] Add the runtime peer violation case in tests/test_architecture.py and verify focused behavior/architecture checks.

## Phase 3: Documentation update

- [x] T007 [P] Update README.md, specs/000-baseline/spec.md, docs/runtime-isolation.md and docs/current-contracts.md.
- [x] T008 [P] Update canonical corp-skills clearml-yolo usage/evaluation guidance in an isolated worktree; validate its metadata, links, Markdown and discovery; record companion evidence in verification.md.
- [x] T009 Validate project Markdown/new files and changed command examples; record results in verification.md.

## Phase 4: Acceptance and delivery

- [x] T010 Run full routine pytest, Ruff, mypy, Vulture and import contracts; record results in verification.md.
- [x] T011 Obtain fresh independent review of final application/companion diffs and checks; reconcile architecture.json and validate acceptance.
- [ ] T012 Commit verified changes, land on master and complete native Git-only release with exact local uv override preservation; record delivery in release.md.
- [ ] T013 Publish the validated companion documentation patch release and verify application/companion remote refs in release.md.

## Dependencies and ownership

T001–T003 precede T004; T004 precedes T005, then T006. Parent owns runtime/tests
and project documentation. T007 and T008 are independent after the approved
contract; the bounded companion delegate owns only its isolated corp-skills
checkout. T009–T010 follow implementation/documentation. Fresh independent review
T011 follows parent verification. T012 precedes companion publication T013.
No other implementation parallelism is necessary for this small change.
