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

## Phase 5: Approved recovery compatibility amendment (2026-10-05)

Earlier checked tasks remain completed historical cleanup work. The current recovery-only
amendment supersedes T004's former rejection goal; it does not reopen other completed work.

- [X] T012 Record approved recovery amendment in `spec.md`, `plan.md`, `research.md`, `data-model.md` and `contracts/task-recovery.md`, preserving completed history (AR-001–AR-006).
- [X] T013 [P] [US4] Add focused threshold recovery cases and implement ordered supported payload readers in `src/clearml_yolo/clearml_models.py` and `tests/test_clearml_models.py` (AR-001, AR-002; depends on T012).
- [X] T014 [US4] Implement deterministic selected-only checkpoint recovery and shared truthful provenance in `src/clearml_yolo/clearml_models.py` and `tests/test_clearml_models.py` (AR-003, AR-004; same recovery owner as T013; depends on T012).
- [X] T015 [P] [US4] Integrate one recovery selection into `src/clearml_yolo/tasks/compare.py` and affected configuration consumers/tests; verify both historical positions use current images/settings and frozen thresholds (AR-004, AR-005; depends on T012, final integration on T013–T014).
- [X] T016 Parent inspects combined recovery/integration diff and runs focused/regression tests and affected static gates, preserving dependency pins and unrelated changes (AR-001–AR-006; depends on T013–T015).
- [X] T017 Verify real source recovery and fresh paired current-image inference when available; record dated outcomes, dashboard/architecture limits and cleanup in feature verification evidence (AR-004–AR-006; depends on T016).

## Phase 6: Compatibility documentation update and acceptance

- [X] T018 Reconcile README, `docs/project-contracts.md`, `docs/current-contracts.md`, affected 001/008/010/012 recovery contracts/spec annotations and quickstarts with the actual implementation; preserve publication/history (AR-001–AR-006; depends on T013–T015).
- [X] T019 Validate changed Markdown, local links and documented recovery examples; record evidence in this feature without claiming new native outcomes (AR-006; depends on T018).
- [X] T020 Parent obtains fresh independent read-only review of combined diff and evidence, resolves findings and records final acceptance (AR-001–AR-006; depends on T016–T019).

T013/T014 share one recovery owner and are sequential within that agent; T015 runs independently
with the parent. Documentation drafting can run in parallel, but T018 requires the final code
reconciliation. Verification checkboxes remain unchecked until actual acceptance evidence exists.

## Documentation amendment evidence (2026-10-05)

T018 reconciled the recovery and comparison diff with the maintained contract: selected-only
checkpoint downloads/provenance, all threshold source priorities, uploaded `.csv.gz`, single
value threshold columns, strict preferred-source errors and explicit dashboard provenance
warnings. No CLI schema or command syntax changed; the existing task references/settings
remain applicable. README is Russian; other changed guidance is English.

T019 parsed changed Markdown with the installed `markdown_it` CommonMark/table parser,
checked fenced-block balance, final newlines/trailing whitespace and local file/heading
links. `git diff --check` passed. These documentation checks do not establish native execution
or ClearML uploads; parent acceptance is recorded below.

## Parent acceptance (2026-10-05)

T013–T017/T020 are complete with [dated verification](verification-2026-10-05.md): full
regression and static gates passed, final focused runs covered all added recovery/comparison
cases, both mixed-role real CPU comparisons completed with frozen thresholds/current-image
membership, downloaded artifacts were inspected, and owned resources were cleaned. Fresh
read-only code/docs and native-evidence reviews returned **ship**, with no blocking findings.
The record retains random-fixture, GPU/training/launcher and historical-architecture limitations.
No commits, dependency revisions, installed tooling changes or unrelated edits were included.
