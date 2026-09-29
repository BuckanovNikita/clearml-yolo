# Tasks: Reusable datasets and native ClearML tracking

**Input**: spec.md, plan.md, research.md, data-model.md and contracts.
**Tests**: Explicitly requested; add regression tests before corresponding implementation.
**Ownership**: D=dataset delegate; N=native delegate; R=reporting delegate; P=parent.

## Phase 1: Setup

- [x] T001 Preserve baseline and isolated dependencies; inspect hooks and document source baseline in specs/008-dataset-clearml-tracking/resume.md (P; FR-013).
- [x] T002 Amend governance and resolve design/checklist consistency in .specify/memory/constitution.md and specs/008-dataset-clearml-tracking/ (P; FR-001–FR-013).

## Phase 2: Foundational

- [x] T003 Freeze cache/publication/model interfaces in specs/008-dataset-clearml-tracking/contracts/ and plan.md; validate requirements analysis (P; FR-003, FR-007–FR-009).

## Phase 3: US1 - Dataset reuse (P1)

Goal: repeated training reuses one safe dataset and readable original filenames.
Independent acceptance: zero repeat image copies/conversion, correct changed identity and split/collision errors.

- [x] T004 [P] [US1] Add hit/change/concurrent/interruption/corruption/split/default-root tests in tests/test_dataset_cache.py (D; FR-001, FR-003, FR-004; SC-001).
- [x] T005 [US1] Add NDJSON filename/casing/stem collision regressions in tests/test_dataset_export.py and tests/test_dataset.py (D; FR-002).
- [x] T006 [US1] Implement versioned atomic per-entry cache and consumer lock in src/clearml_yolo/dataset_cache.py; required files exist and requested splits contain at least one image (D; FR-001, FR-003, FR-004).
- [x] T007 [US1] Preserve NDJSON names, flat compatibility and final-path diagnostics in src/clearml_yolo/dataset_export.py and src/clearml_yolo/dataset.py (D; FR-002, FR-003).
- [x] T008 [US1] Wire dataset_cache_dir and direct cached YAML training in src/clearml_yolo/tasks/train.py, tasks/pipeline.py, configs.py and config_tree.py; add tests/test_train.py, test_pipeline.py, test_configs.py, test_config_tree.py coverage (P; FR-001, FR-004; depends T006–T007).

## Phase 4: US2 - Native tracking and best model (P1)

Goal: native previews, one truthful best model, owner lifecycle and completion guarantees.
Independent acceptance: installed callback set runs only owner, settings restore, publication failures fail.

- [x] T009 [P] [US2] Add callback/worker/settings restoration and registration failure tests in tests/test_native_runtime.py and tests/test_clearml_native.py (N; FR-005, FR-006).
- [x] T010 [US2] Implement native callback scope and same-model metadata enrichment in src/clearml_yolo/native_runtime.py and src/clearml_yolo/clearml_native.py (N; FR-005, FR-006).
- [x] T011 [US2] Add model upload/flush/interruption barriers and rejection tests in src/clearml_yolo/clearml_session.py and tests/test_clearml_session.py (N; FR-007; SC-002, SC-004).
- [x] T012 [US2] Wire native registration/finalization in src/clearml_yolo/tasks/train.py and tests/test_train.py; remove broad native checkpoint/plot uploads (P; FR-005–FR-008; depends T010–T011 and T008).

## Phase 5: US3 - Readable publications (P1)

Goal: canonical useful tables/workbooks and configurations, no diagnostic or duplicated artifacts.
Independent acceptance: exact standalone and pipeline inventories including empty predictions and skipped stages.

- [x] T013 [US3] Implement canonical table deduplication, internal expectation aliases, run configuration and config-without-artifact adapters in src/clearml_yolo/clearml_session.py; extend tests/test_clearml_session.py (N; FR-008, FR-009; depends T011).
- [x] T014 [P] [US3] Add readable inventory and workbook/threshold precision regressions in tests/test_metrics.py, test_predict.py, test_report.py, test_publishing.py (R; FR-008, FR-009; SC-003).
- [x] T015 [US3] Publish canonical prediction/truth CSVs and retain local replay manifests/YAML in src/clearml_yolo/tasks/predict.py (R; FR-008, FR-009).
- [x] T016 [US3] Publish one exact validation CSV and consolidated evaluation XLSX per split in src/clearml_yolo/tasks/metrics.py and src/clearml_yolo/artifact_names.py (R; FR-008, FR-010).
- [x] T017 [US3] Remove duplicate report inputs and remote diagnostic receipts in src/clearml_yolo/tasks/report.py and tasks/publication.py (R; FR-008, FR-009).
- [x] T018 [US3] Wire canonical configuration remote-clone replay and remove source-Hydra/diagnostic copies in src/clearml_yolo/apps/common.py; add tests/test_publication_commands.py (P; FR-009; depends T013).
- [x] T019 [US3] Assert combined exact inventories and skipped-stage behavior in tests/test_publication_commands.py and tests/test_pipeline.py; update ground-truth publication in src/clearml_yolo/tasks/ground_truth.py (P; FR-007–FR-009; SC-003; depends T015–T018).

## Phase 6: US4 - Comparison autodiscovery (P2)

Goal: new and historical model sources compare paired current-test results with exact thresholds.
Independent acceptance: native best selection, historical readers and local references all covered.

- [x] T020 [P] [US4] Add explicit best-model/ambiguity/CSV/historical reader regressions in tests/test_clearml_models.py (P; FR-010, FR-012).
- [x] T021 [US4] Implement source model links, best selection and validation threshold CSV reads in src/clearml_yolo/clearml_models.py; unique nonempty class names and finite confidence in [0,1] (P; FR-010, FR-012).
- [x] T022 [US4] Replace comparison payload dumps/config copies with shared configuration, paired CSVs and one workbook in src/clearml_yolo/tasks/compare.py and comparison/reinfer.py; retain local diagnostics/manifests (P; FR-011; depends T013, T021).
- [x] T023 [US4] Add source links/checkpoint design to workbook and regressions for prod exclusion, automatic skip, explicit failure, local inputs and frozen thresholds in tests/test_comparison_reinfer.py, test_comparison_workbook.py and test_publication_commands.py (P; FR-010–FR-012; SC-004; depends T022).

## Phase 7: Verification and cross-cutting acceptance

- [x] T024 Update README.md in Russian, AGENTS.md, skills/running-end-to-end-tests references and affected existing contracts under specs/001-release-030, specs/003-ultralytics-config-groups, specs/005-explicit-detection-config and specs/007-detection-config-cleanup (P; FR-013).
- [x] T025 Run pytest/Ruff/mypy/import/pre-commit and Markdown/link validation; inspect complete feature diff; record dated evidence in docs/evidence/2026-09-29-dataset-clearml-tracking.md (P; FR-013; SC-001–SC-004).
- [x] T026 Run real CPU/GPU training/cache reuse, native previews and downloaded model metadata acceptance, new/historical paired comparison and failure scenarios via specs/008-dataset-clearml-tracking/quickstart.md; record portable evidence in docs/evidence/2026-09-29-dataset-clearml-tracking.md (P; SC-001–SC-004).
- [x] T027 Run speckit-converge against current source and specs/008-dataset-clearml-tracking/tasks.md; implement appended gaps until clean (P; FR-001–FR-013).
- [x] T028 Obtain fresh read-only gpt-5.6-sol/high ASTRA REVIEW ship after parent verification; record review and telemetry availability in docs/evidence/2026-09-29-dataset-clearml-tracking.md (P; all acceptance criteria).

## Dependencies and parallel execution

Setup -> foundational -> independent US1/US2/US3 test packages and parent US4 reader tests.
US1 cache -> parent train integration. US2 session and runtime -> native train integration.
US3 adapter interface is frozen at T003; reporting code can develop against it independently,
but integration waits for T013. Native delegate runs T009–T011 then T013 sequentially in its
owned files. Parent never writes those files concurrently. Reporting delegate owns only T014–T017.
US4 readers can start independently; comparison publication waits for adapter implementation.
All stories must pass before cross-cutting acceptance. No delegated commits or task-marker edits.

Parallel examples: T004 (dataset tests), T009 (native tests), T014 (reporting tests), T020
(parent reader tests) use disjoint files. Within each package tests precede implementation.

## Implementation strategy

US1 is the MVP increment; user acceptance requires all four stories and all verification gates.
Review custom checklists separately from implementation markers. Preserve native forwarding,
immutable source images, pinned dependencies and historical tasks. Do not commit or push.

## Phase 8: Convergence

- [x] T029 Reject default as well as explicit cache roots nested inside run-owned output directories in dataset_cache.py, tasks/train.py and tasks/pipeline.py; add regression coverage in tests/test_train.py and tests/test_pipeline.py per FR-004 (partial, HIGH).

- [x] T030 Preserve executable local/remote credentials while sanitizing canonical run storage in clearml_session.py; add replay regressions in tests/test_clearml_session.py per FR-009 (partial, HIGH).

## Phase 9: Convergence

- [x] T031 Replace duplicate prediction requested/effective parameter copies with meaningful native normalization differences in tasks/predict.py and tests/test_predict.py per FR-009 (partial, MEDIUM).

## Phase 10: Convergence

- [x] T032 Preserve native DDP training compatibility while keeping all ClearML publication in the invocation owner; add a local native-event replay/relay boundary and tests, integrate training, and verify model registration per FR-005, FR-007 and FR-013 (partial, HIGH). Installed Ultralytics suppresses integration callbacks in the launching DDP parent, so owner-only worker suppression currently leaves no native model.

## Phase 11: Convergence

- [x] T033 Keep prior invocation-derived General project/name/save_dir out of remote clone replay while preserving current requested output routing and native parameter overrides; add train/pipeline clone regressions in apps/common.py and tests/test_publication_commands.py per FR-009 and Constitution III (partial, HIGH; independent review).

## Phase 12: Convergence

- [x] T034 Preserve a current explicit save_dir key through remote General replay so pipeline routing rejects the conflict exactly as local execution does; retain removal of inherited-only save_dir and add launch regressions per FR-009, FR-013 and Constitution III (partial, MEDIUM; second independent review).
