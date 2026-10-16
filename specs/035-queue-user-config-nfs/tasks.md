# Tasks: Per-user queue settings and NFS coordination

## Setup and foundation

- [x] T001 Inspect current source/contracts and capture requirements in spec.md.
- [x] T002 Validate plan.md and architecture.json before implementation.

## User Story 1: required per-user settings

- [x] T003 [US1] Add failing lookup, override, missing/incomplete and two-user tests in tests/test_queue_settings.py.
- [x] T004 [US1] Implement config discovery and actionable errors in src/clearml_yolo/adapters/queue/settings.py and help in src/clearml_yolo/entrypoints/queue.py.

## User Story 2: eligible NFS coordination

- [x] T005 [US2] Add failing effective mount-option, nested/escaped/malformed mount tests in tests/test_queue_settings.py.
- [x] T006 [US2] Implement bounded NFS eligibility in src/clearml_yolo/adapters/queue/settings.py.
- [x] T007 [US2] Run existing binding/namespace/guardian/recovery/process regressions and record verification.md.

## Documentation update and acceptance

- [x] T008 Update README.md, TECH_DETAILS.md, docs/queue.md, docs/filesystem-policy.md, docs/project-contracts.md and docs/current-contracts.md.
- [x] T009 [P] Update canonical corp-skills clearml-yolo usage/evaluation package and validate it; link dated evidence in verification.md.
- [x] T010 Run static/import/architecture/docs/example checks; obtain fresh independent review and validate architecture.json acceptance.
- [x] T011 Complete native checked commit/release, isolated installed CLI verification, companion release and preservation checks in release.md.

## Dependencies and strategy

T001→T002→T003→T004; T005→T006 follows the shared settings edit. T007 follows both.
T008/009 can proceed independently once behavior is integrated. Parent owns application
code/docs; bounded companion agent owns its separate repository. T010 follows all
implementation/docs; T011 follows acceptance. No parallel edits to settings.py.
