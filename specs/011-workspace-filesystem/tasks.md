# Tasks: Workspace-owned filesystem defaults

> Historical path note (2026-10-02): `src/clearml_yolo/native_dataset.py` and
> `tests/test_native_dataset.py` named in completed tasks below were removed by
> [feature 012](../012-remove-legacy-compatibility/spec.md). The entries remain as completed history.

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [filesystem contract](contracts/filesystem-ownership.md)

**Verification**: [Dated checks and limitations](verification-2026-10-01.md)

> **History note:** This ledger was created after implementation was substantially underway.
> Checked implementation tasks reflect inspected code and supplied targeted evidence; unchecked
> tasks preserve the remaining final verification and documentation gates.

**Tests**: Observable path, warning, source-preservation and cleanup regressions are required.

## Phase 1: Intent and design

- [x] T001 Inspect current filesystem writes, dependency defaults, source-data mutation risks and
  maintained contracts in `src/clearml_yolo/`, `tests/`, `docs/` and affected `specs/` (FR-001–012).
- [x] T002 Create and quality-check `specs/011-workspace-filesystem/spec.md` and
  `checklists/requirements.md` from the approved behavior and materialization status.
- [x] T003 Record design decisions, entities, compatibility contract and validation examples in
  `research.md`, `data-model.md`, `contracts/filesystem-ownership.md` and `quickstart.md`.
- [x] T004 Confirm that no material clarification remains: explicit paths stay valid anywhere,
  physical-home targets warn without rejection, and the policy is not an OS sandbox.

## Phase 2: Startup and workspace defaults

**Goal**: Capture one workspace and initialize missing dependency defaults before app imports.

- [x] T005 [US1] Add workspace, warning, model-path and temporary-root helpers in
  `src/clearml_yolo/filesystem.py` with subprocess coverage in `tests/test_filesystem.py`
  (FR-001–005, FR-009, FR-011–012).
- [x] T006 [US1] Initialize package bytecode and app dependency defaults in
  `src/clearml_yolo/__init__.py` and `src/clearml_yolo/apps/__init__.py`; route Hydra/run defaults
  through the workspace in `src/clearml_yolo/configs.py` and `src/clearml_yolo/run_identity.py`
  (FR-001–003, FR-011).
- [x] T007 [US2] Preserve explicit XDG, ClearML, temporary, FiftyOne and native directory values;
  add physical-symlink home warnings and read-only existing-config tests in
  `tests/test_filesystem.py` (FR-003–005).

## Phase 3: Native inputs and runtime

**Goal**: Prevent native cache/repair writes from touching source data and scope native globals.

- [x] T008 [US3] Add real image/label staging, atomic entry publication and lifetime locking in
  `src/clearml_yolo/native_dataset.py`, and integrate it with native training in
  `src/clearml_yolo/tasks/train.py` (FR-006).
- [x] T009 [US3] Add source-preservation, native `.npy`/label-cache and reuse regressions in
  `tests/test_native_dataset.py` (FR-006; SC-003).
- [x] T010 [US1] Scope default native dataset/weight/run and DDP launcher directories, preserving
  explicit settings and restoring globals in `src/clearml_yolo/native_runtime.py` and affected
  runtime tests (FR-007).
- [x] T011 [US3] Route only absent bare `.pt` names to the workspace weight cache in
  `src/clearml_yolo/inference.py` and `src/clearml_yolo/clearml_models.py`; preserve explicit and
  remote references in affected model tests (FR-009).

## Phase 4: Temporary ownership and integration

**Goal**: Keep invocation-owned temporary work contained and preserve atomic output behavior.

- [x] T012 [US4] Move resolved execution configurations into workspace temporary storage and
  preserve rootless native-YAML path semantics in `src/clearml_yolo/clearml_session.py` and
  `tests/test_clearml_session.py` (FR-008).
- [x] T013 [US4] Route inference and DDP relay/runtime files through workspace temporary storage
  in `src/clearml_yolo/inference.py`, `src/clearml_yolo/native_ddp.py` and affected tests (FR-008).
- [x] T014 [US4] Keep atomic comparison partial files beside the selected output and prove cleanup
  on serialization/replacement failures in `src/clearml_yolo/comparison/` and
  `tests/test_filesystem.py`/comparison tests (FR-010).
- [x] T015 [US1] Route task output producers, dataset defaults and generated configuration comments
  through the workspace contract in affected `src/clearml_yolo/tasks/`, `dataset_cache.py`,
  `config_tree.py` and integration tests (FR-001–003, FR-008).

## Phase 5: Verification and convergence

- [x] T016 Run the final affected pytest selection after the native-dataset assertion correction,
  including startup write auditing, native runtime, configuration, model, training and atomic
  publication behavior (SC-001–004).
- [x] T017 Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .` and `uv run lint-imports`;
  record exact results and distinguish mocked checks from real execution evidence (SC-005;
  Constitution IV).
- [x] T018 Inspect the complete implementation diff, perform final independent review and rerun
  Spec Kit convergence against this ledger; append any remaining buildable gaps without rewriting
  completed history.

## Phase 6: Documentation update

**Purpose**: Reconcile maintained contracts with the final implementation and validate them.

- [x] T019 [P] Update filesystem defaults, native staging and temporary ownership in
  `specs/001-release-030/contracts/cli.md`, `specs/008-dataset-clearml-tracking/` and
  `specs/009-resolved-config-uploads/`; annotate the superseded historical T022 intent without
  changing its completion marker (depends on T012–T015).
- [x] T020 [P] Update portable integration guidance in
  `.agents/skills/running-end-to-end-tests/SKILL.md` and
  `.agents/skills/running-end-to-end-tests/references/pipeline-prerequisites.md` (depends on T008–T015).
- [x] T021 Reconcile parent-owned `README.md`, `docs/filesystem-policy.md` and
  `docs/current-contracts.md` against the final code and documentation diff (depends on T016–T018).
- [x] T022 Validate all changed Markdown and local links, and check documented path/launcher
  examples against current behavior (depends on T019–T021).

## Dependencies and execution order

T001–T004 establish intent. T005–T007 establish shared startup behavior. T008–T011 depend on that
workspace policy; T012–T015 depend on the same helpers and integrate independent consumers. T016
follows the final implementation changes; T017 and T018 follow T016. Documentation tasks T019 and
T020 follow their implementation dependencies and may proceed in parallel. Parent-owned T021 and
final validation T022 remain after the complete code diff and final checks.

## Requirement coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T001, T005, T006, T015, T016 |
| FR-002 | T005, T006, T015, T016 |
| FR-003 | T005–T007, T015, T016 |
| FR-004 | T005, T007, T016 |
| FR-005 | T005, T007, T016 |
| FR-006 | T008, T009, T016 |
| FR-007 | T010, T016 |
| FR-008 | T012, T013, T015, T016 |
| FR-009 | T005, T011, T016 |
| FR-010 | T014, T016 |
| FR-011 | T005, T006, T019–T022 |
| FR-012 | T004, T019–T022 |
| SC-001 | T005–T007, T016 |
| SC-002 | T007, T016 |
| SC-003 | T008, T009, T016 |
| SC-004 | T012–T014, T016 |
| SC-005 | T017, T018, T021, T022 |

## Implementation strategy

Treat the inspected implementation as provisional until T016–T018 pass. Complete and validate the
documentation phase only after the final code surface is stable. Do not infer native GPU execution,
ClearML upload success or an operating-system sandbox from mocked tests.

## Phase 7: Convergence

- [x] T023 Preserve native image membership, duplicates, source ordering and both cwd-relative
  and `./` manifest entries in `src/clearml_yolo/native_dataset.py`; compare against the installed
  native reader in `tests/test_native_dataset.py` (FR-006, partial; independent review).
- [x] T024 Publish and return the expanded path produced by `build_ground_truth()` in
  `src/clearml_yolo/tasks/ground_truth.py`; add a tracked conversion regression in
  `tests/test_ground_truth.py` (FR-003, partial; independent review).

## Phase 8: Convergence

- [x] T025 Include resolved text-manifest membership in native cache identity and prove reuse
  cannot select another working directory's images in `src/clearml_yolo/native_dataset.py` and
  `tests/test_native_dataset.py` (FR-006, partial; second independent review).
- [x] T026 Make staged images and labels owner-writable while retaining read-only source
  permissions; verify `0444` fixtures in `tests/test_native_dataset.py` (FR-006, partial;
  second independent review).
- [x] T027 Clarify specification input wording and native cache/permission documentation in
  `spec.md`, `plan.md`, `data-model.md`, `research.md`, `contracts/filesystem-ownership.md` and
  `docs/filesystem-policy.md`; retain FR-004's warnings for every physical-home write destination
  and validate Markdown/links (FR-004, FR-006; documentation clarification).

## Phase 9: Convergence

- [x] T028 Preserve explicitly configured native dataset directories during NDJSON/platform
  conversion; verify both default and explicit selections in `src/clearml_yolo/native_dataset.py`
  and `tests/test_native_dataset.py` (FR-003, FR-007, partial; parent follow-up inspection).

## Phase 10: Documentation update and validation

- [x] T029 Record accepted final review, clean convergence and correction evidence in
  `verification-2026-10-01.md`; reconcile the native membership/permission/directory changes with
  `docs/filesystem-policy.md` and this feature's design documents, then validate all changed
  Markdown and local links (depends on T023–T028 and final independent acceptance).

## Phase 11: Convergence

- [x] T030 Preserve original remote, bare and explicit relative checkpoint references through
  the pipeline prediction handoff; verify `src/clearml_yolo/tasks/pipeline.py` against pipeline
  regressions and model resolution checks (FR-009, partial; third independent review).

## Phase 12: Documentation update and validation

- [x] T031 Record the pipeline handoff correction and accepted final verification in
  `verification-2026-10-01.md`; confirm model-reference guidance in `docs/filesystem-policy.md`
  and `contracts/filesystem-ownership.md`, then validate final Markdown and local links
  (depends on T030 and final independent acceptance).

## Phase 13: Workspace boundary correction

The earlier completed tasks and dated verification above describe the implementation at the time
they ran. They do not establish the corrected boundary below.

- [x] T032 Restrict startup defaults to application-owned storage plus Ultralytics downloaded
  datasets/weights/settings, ClearML downloads/cache and FiftyOne dataset/dataset-zoo/database
  directories. Restore ordinary general XDG, compute/library cache/config, Python bytecode,
  ETA/FiftyOne model/plugin/config and generic process/tempfile behavior; preserve explicit values,
  FiftyOne configured data paths and the ClearML legacy alias (FR-002, FR-003, FR-005, FR-011).
- [x] T033 Make `dataset_cache_dir=null` always select
  `CY_HOME/.cache/clearml-yolo/datasets` independently of XDG and retain explicit values; add or
  update regression coverage for the corrected selections (FR-013).
- [x] T034 Reconcile `README.md`, `docs/filesystem-policy.md` and this feature's current intent,
  design, validation guide and compatibility contract. Annotate superseded research without
  rewriting prior completion history or dated verification.
- [x] T035 Run affected tests and project gates, validate changed Markdown/local links after the
  final code diff, obtain independent review, and record new dated evidence without claiming native
  GPU execution or remote ClearML upload verification.

Correction evidence: [2026-10-01 workspace cache boundary verification](../../.specify/bugs/workspace-cache-boundary/test.md).
