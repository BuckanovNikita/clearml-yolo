# Tasks: Detection configuration cleanup

## Setup and foundation

- [x] T001 Inspect implementation, dependencies and constitution; capture design in spec.md and plan.md.
- [x] T002 Complete clarification and cross-artifact coverage review for specs/007-detection-config-cleanup/.

## US1 - Focused editable examples

Independent test: generated commands compose; devices independent; runtime values retained.

- [x] T003 [US1] Add regression tests in tests/test_configs.py and tests/test_config_tree.py (FR-001–003).
- [x] T004 [US1] Implement device defaults and example sections in src/clearml_yolo/native_config.py and config_tree.py.

## US2 - Task-derived output roots

Independent test: actual task identity, unsafe names, distinct IDs and explicit routes.

- [x] T005 [US2] Add identity and routing regressions in tests/test_run_identity.py and tests/test_pipeline.py (FR-004).
- [x] T006 [US2] Add adapter/plain-value routing in src/clearml_yolo/clearml_session.py and run_identity.py; wire apps/common.py and tasks/.

## US3 - Complete split evidence

Independent test: three splits yield 39 successful split artifacts and one eligible receipt.

- [x] T007 [US3] Add parity, matching, zero-prediction, missing-output/upload and publication regressions in tests/test_metrics.py and tests/test_pipeline.py (FR-005–009).
- [x] T008 [US3] Centralize inventory in src/clearml_yolo/artifact_names.py and tasks/metrics.py; update configs.py and direct-call defaults.

## Documentation and verification

- [x] T009 Update README.md, generated guidance and affected contracts for FR-010.
- [x] T010 Run pytest, Ruff, mypy, import-linter and documentation checks; record docs/evidence/2026-09-29-detection-config-cleanup.md.
- [x] T011 Run isolated real three-split acceptance, download artifacts and inspect publication; record dated evidence and clean task-owned resources.
- [x] T012 Review combined diff and dependency pins, address findings and finalize evidence.

## Dependencies and strategy

T001→T002 precede implementation. Each story's regression task precedes implementation.
US1 and US2 are independently testable; US3 integrates their routing/configuration outputs.
T009 follows stories; T010→T011→T012 close verification. Implement incrementally in place
on the feature branch, preserving initialized submodules and the existing environment.
Parallel opportunities: independent regression reviews for US1/US2; no concurrent writes needed.

## Execution ledger

- Pre-flight: example export→Hydra composition must retain controlled keys; task identity→
  filesystem helper accepts only plain values; metrics→publication retains evaluation paths.
- Ruling: use the clean checkout on a new feature branch, preserving initialized submodules;
  no worktree/commit is needed for this authorized uncommitted implementation.

- Final review: reserve the project component latest to avoid the convenience symlink;
  both fresh/existing-link cases reproduced, then passed after encoding the reserved name.
- Final review: native training default name now follows actual task name after remote
  rename; regression reproduced requested-name drift and passed after adapter integration.
- Test corrections: payload indices are stable source indices, not split-local list
  positions; tests resolve by index. Runtime YAML tests materialize OmegaConf containers.

- Verification: final pytest 515 passed / 8 opt-in skipped; real database tests 8 passed;
  Ruff, strict mypy and nine import contracts passed. See the dated repository evidence.
- Live acceptance: two pipelines, metrics/subset/disabled, validation and prediction
  completed with downloaded artifacts; injected upload rejection/interruption failed as
  expected and retained local diagnostics. Final artifact/routing/replay audit passed.
- Cleanup: removed the exact tagged ClearML project/tasks, owned FiftyOne dataset and
  local synthetic run; stopped owned MongoDB, released its port reservation and archived
  evidence in the global environment skill. No pending implementation or verification tasks.
