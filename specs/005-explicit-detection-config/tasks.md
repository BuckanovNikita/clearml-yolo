# Tasks: Explicit Detection Configuration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [contracts](contracts/native-configuration.md).
**Tests**: Behavior-first regressions required. No commit or push.

**Final clarification**: The user corrected the default image size to 960; 906 is retained
only as an explicit normalization test case and in dated pre-correction evidence.

> **Current-contract note:** Checked tasks preserve completed feature history. Requested and
> effective native YAML now stays local; ClearML replay uses canonical run configuration and
> native General parameters. T011's downloaded-configuration wording records the acceptance
> method used at that time. See [current contracts](../../docs/current-contracts.md).

## Phase 1: Setup

- [X] T001 Capture accepted clarifications and create specification/design artifacts in specs/005-explicit-detection-config/ (FR-001–FR-008).
- [X] T002 Audit all installed parameters and review requirements/checklist and cross-artifact consistency; record research.md and analysis.md (SC-001).

## Phase 2: Foundational Tests

- [X] T003 Write and observe failing configuration regressions in tests/test_native_config.py, tests/test_config_tree.py and tests/test_configs.py (FR-001–FR-005).
- [X] T004 [P] Write and observe failing invocation/normalization regressions in tests/test_inference.py and affected tests/test_train.py, tests/test_predict.py, tests/test_compare.py, tests/test_pipeline.py (FR-004–FR-007).

## Phase 3: US1 — Inspect Useful Parameters

**Goal**: Complete, documented detection examples.
**Independent test**: Exported examples compose like built-in groups with only applicable keys active.

- [X] T005 [US1] Implement classification, canonical defaults, complete export and explicit references in src/clearml_yolo/native_config.py, configs.py and config_tree.py (FR-001–FR-003; SC-001).

## Phase 4: US2 — Execute the Configuration Shown

**Goal**: Native calls use the resolved owning group.
**Independent test**: Native call capture across all model commands, including paired comparison.

- [X] T006 [US2] Require complete resolved settings and remove runtime merges/fallbacks in src/clearml_yolo/native_config.py (FR-004–FR-005).
- [X] T007 [US2] Remove helper/comparison defaults and adapt train/predict/val/pipeline/compare consumers in src/clearml_yolo/inference.py and tasks/ (FR-005–FR-006; SC-002).

## Phase 5: US3 — Explain Effective Behavior

**Goal**: Configured values and native normalization remain distinct and inspectable.
**Independent test**: Requested/effective records retain image size and actual native shape.

- [X] T008 [US3] Record requested and effective settings/shape across src/clearml_yolo/inference.py and tasks/ (FR-007).
- [X] T009 [US3] Update README.md and relevant portable configuration guidance/contracts for migration and ownership (FR-008).

## Phase 6: Verification and Convergence

- [X] T010 Run pytest, Ruff, mypy, import-linter and applicable pre-commit checks; record dated verification evidence (SC-001–SC-002).
- [X] T011 Follow integration/environment skills for real training, prediction, paired comparison and downloaded configuration artifacts; record dated evidence (SC-003).
- [X] T012 Run Spec Kit convergence and independent read-only review, resolve findings, and record final coverage in verification-2026-09-29.md (FR-001–FR-008).

## Dependencies and Ownership

T001→T002→T003/T004. Configuration owner: T003/T005/T006 and their named files only.
Runtime owner (parent): T004/T007/T008 and runtime tests, then documentation/evidence.
T007 integrates T006's agreed interface. T010/T011 follow integrated implementation;
T012 follows verification and appends remaining work if necessary. Reviewers do not edit code.
