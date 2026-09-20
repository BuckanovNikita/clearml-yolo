# Tasks: clearml-yolo 0.3.0

Input: spec.md, plan.md, research.md, data-model.md and contracts/ in this directory.
Tests are required by the supplied release acceptance plan.

## Phase 1: Setup

- [X] T001 Amend .specify/memory/constitution.md to 2.0.0 and retain Spec Kit templates/feature.json per FR-015.
- [X] T002 Record release spec/design/contracts and analyze coverage in specs/001-release-030/ per FR-001–FR-015.

## Phase 2: Foundational

- [X] T003 Verify ignores, external-library contracts and baseline checks in .gitignore and specs/001-release-030/research.md per plan.
- [X] T004 Define cross-component ownership and evaluation interfaces in specs/001-release-030/contracts/ per FR-010–FR-014.

## Phase 3: User Story 1 — Native model execution (P1)

Goal: run model parameters without hidden automation. Independent test: YAML/embedded equivalence.

- [X] T005 [US1] Add failing precedence/explicit-default/removed-option tests in tests/test_configs.py and tests/test_ultralytics_params.py per FR-001, FR-005, SC-001.
- [X] T006 [US1] Implement sparse native mappings and source overlay in src/clearml_yolo/configs.py per FR-001.
- [X] T007 [US1] Add forwarding/output/DDP parent contract tests in tests/test_train.py and tests/test_predict.py per FR-002–FR-003.
- [X] T008 [US1] Delegate native execution and record actual arguments/paths in src/clearml_yolo/tasks/train.py, tasks/predict.py and inference.py per FR-002.
- [X] T009 [US1] Remove gpu.py, run_queue.py, queue_view.py, augment.py, config_tree.py, obsolete apps/tests/configs and update pyproject.toml contracts per FR-005.

## Phase 4: User Story 2 — Current-data evaluation (P1)

Goal: frozen-threshold current-test comparison. Independent test: counts/thresholds agree across reports.

- [X] T010 [P] [US2] Add calibration/membership/empty-image/class/missing-input tests in tests/test_metrics.py and tests/test_comparison_scoring.py per FR-006–FR-010, SC-002.
- [X] T011 [US2] Implement calibration once on val and fixed evaluation in src/clearml_yolo/tasks/metrics.py and comparison/scoring.py; required thresholds must be finite and within [0,1], missing required classes fail explicitly, per FR-007.
- [X] T012 [US2] Implement baseline selection excluding current task and missing/explicit failure semantics in src/clearml_yolo/clearml_models.py and tasks/compare.py per FR-008.
- [X] T013 [US2] Share current-test paired evaluated results with statistical and developer/business builders in src/clearml_yolo/tasks/compare.py, tasks/report.py and comparison/ per FR-009–FR-010.
- [X] T014 [US2] Add cy-val and integrate isolated pipeline routing/skip-stage validation in src/clearml_yolo/tasks/val.py, tasks/pipeline.py and apps/ per FR-003–FR-004.
- [X] T015 [US2] Verify dataset ingestion and cross-command report/count consistency in tests/test_ground_truth.py, tests/test_pipeline.py and tests/test_report.py per FR-006, FR-010.

## Phase 5: User Story 3 — Complete tracking (P1)

Goal: exactly one complete task. Independent test: required upload rejection fails invocation.

- [X] T016 [P] [US3] Add lifecycle/worker/upload/interruption/redaction tests in tests/test_clearml_session.py per FR-011–FR-014, SC-003.
- [X] T017 [US3] Implement required tracking owner, synchronous artifact manifest and failure handling in src/clearml_yolo/clearml_session.py per FR-011, FR-013–FR-014.
- [X] T018 [US3] Capture sanitized sources/resolved configuration/dataset/effective args/model refs/methodology and suppress duplicate native callbacks in src/clearml_yolo/apps/ and tasks/ per FR-011–FR-012.
- [X] T019 [US3] Upload all produced required checkpoint/table/threshold/metric/plot/report outputs in src/clearml_yolo/tasks/ and clearml_report.py per FR-013.

## Phase 6: User Story 4 — Install and migrate (P2)

Goal: usable 0.3.0 distribution. Independent test: clean install exposes exactly eight commands.

- [X] T020 [P] [US4] Update Russian README.md, docs/migration-030.md and remove obsolete docs/superpowers specifications per FR-005, FR-015.
- [X] T021 [P] [US4] Update scripts/agent_env.sh, AGENTS.md and .claude/skills/running-end-to-end-tests/ for explicit devices with preflight/capacity/cleanup per FR-015.
- [X] T022 [US4] Set 0.3.0, update uv.lock, build wheel/sdist and verify clean installation/help/examples via pyproject.toml and docs/evidence/2026-09-19-release-030.md per SC-005.

## Phase 7: Release verification and convergence

- [X] T023 Run pytest, Ruff, mypy, import-linter and pre-commit checks; record commands/results in docs/evidence/2026-09-19-release-030.md per SC-004.
- [X] T024 Run task-owned CPU/GPU workflows, no-baseline and baseline/candidate, cy-val/cy-compare, both styles and artifact downloads; record cleanup and distributed limitation in docs/evidence/2026-09-19-release-030.md per SC-003–SC-004.
- [X] T025 Run speckit-converge and repeat analysis, close acceptance gaps in specs/001-release-030/tasks.md and obtain fresh review per plan.

## Dependencies and parallel execution

T001–T004 precede implementation. US1 and US3 adapter implementation may run independently;
US2 evaluation/scoring may proceed independently with documented tracking interfaces.
T014 integrates US1/US2/US3. US4 follows settled CLI contracts; T020 and T021 may run in parallel.
T023/T024/T022 verification precedes T025 final acceptance. Tests precede corresponding code.

## Implementation strategy

Native execution is the first functional slice; then add frozen evaluation/comparison and
complete tracking integration. No slice alone is release acceptance. Preserve unrelated files,
use task-owned resources and leave unchecked any task whose required evidence is missing.
