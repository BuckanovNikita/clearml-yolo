# Tasks: Remove legacy compatibility

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts](contracts/current-only.md).

## Phase 1: Foundation

- [X] T001 Record approved specification, design decisions, current contracts and task ownership (FR-001–FR-009).
- [X] T002 Amend `.specify/memory/constitution.md` to 6.0.0, preserving prior amendments (FR-008).

## Phase 2: Current behavior

- [X] T003 [P] [US1] Update training rejection/current-path tests; remove native-only training and its module in `src/clearml_yolo/tasks/train.py` and exclusive tests (FR-001, FR-002).
- [X] T004 [P] [US2] Update recovery tests; remove historical weights/threshold readers and obsolete constants in `src/clearml_yolo/clearml_models.py`, `artifact_names.py` (FR-003).
- [X] T005 [US3] Update configuration, prediction helper/callers, comparison evaluation, filesystem and identity tests/source; remove the deleted module's import contract entry (FR-004–FR-006).
- [X] T006 Integrate all results and run focused tests, full pytest, Ruff, mypy and import-linter (FR-009).
- [X] T007 Run isolated real CPU/GPU and ClearML recovery acceptance; clean task-owned resources and record outcomes/limitations (FR-009).

## Phase 3: Documentation update and acceptance

- [X] T008 Update README, `docs/` summary/index/policy, active contracts/specs/quickstarts, project-owned integration guidance and global environment examples; remove migration guides and repair links (FR-007, FR-008; depends on T003–T005).
- [X] T009 Validate changed Markdown, local links and generated command examples; record dated evidence in this feature (FR-007, FR-009; depends on T006–T008).
- [X] T010 Parent inspects combined diff, verifies requirements and obtains fresh read-only review (FR-001–FR-009; depends on T009).

## Dependencies and rulings

T003 and T004 have disjoint write ownership and run in parallel with parent-owned T005.
T006 follows all three; documentation reflects the final implementation. No agent delegates further.
Full hooks are reserved for commit/release work because changelog generation mutates unrelated files.
Template helper persistence is bypassed to preserve the protected feature pointer; artifacts are
authored under this feature and prerequisites resolved with `--paths-only`.

## Phase 4: Convergence

- [X] T011 Repair the historical migration-guide link in `.specify/bugs/excel-match-export/test.md` after explicit approval for that protected file; validate links and obtain fresh read-only acceptance (FR-007; partial).
