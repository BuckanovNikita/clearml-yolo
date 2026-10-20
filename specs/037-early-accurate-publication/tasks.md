# Tasks: Accurate configuration and early complete publication

## Foundation

- [x] T001 Record inspected intent, contracts, scope and architecture in specs/037-early-accurate-publication/.
- [x] T002 Validate architecture plan and analyze requirement coverage in specs/037-early-accurate-publication/architecture.json.
- [x] T003 Extend typed tracking/export ports in src/clearml_yolo/application/ports.py and bind composition in src/clearml_yolo/entrypoints/composition.py.

## User Story 1 — Executable configuration

- [x] T004 [P] [US1] Add configuration/queue/replay/difference regressions in tests/test_model_replay.py and focused new tests; reproduce current publication gaps.
- [x] T005 [P] [US1] Implement selected-default composition, active run and informational overrides in entrypoints/hydra and adapters/clearml/session.py; exclude derived cache input in adapters/clearml/cache.py.
- [x] T006 [US1] Publish validated General before preparation in application/use_cases/train.py, preserving native/detector/DDP lifecycle semantics.

## User Story 2 — Complete artifacts early

- [x] T007 [P] [US2] Add active-invocation ordering/failure regressions for result contributors and complete artifacts in tests/.
- [x] T008 [P] [US2] Implement immediate truth and completed result aggregation in adapters/clearml/results.py and workflow completion sequencing in application/use_cases/.
- [x] T009 [US2] Publish comparison dashboards before later evaluation/statistics and final annotated workbooks at completion in application/use_cases/compare.py and report.py.
- [x] T010 [P] [US2] Add optional typed export notification and immediate finalized-file publication in application/use_cases/export.py, adapters/integrations/export_operations.py and adapters/export/verification.py.

## User Story 3 — Acceptance and delivery

- [x] T011 [US3] Verify skipped/standalone stages, duplicate/conflicting inputs, cancellation, upload failures, cache independence and final barriers in tests/.
- [x] T012 [US3] Run full behavior/static/import checks and add scoped forbidden-edge tests in tests/test_architecture.py.
- [ ] T013 [US3] Run isolated native direct/queued/DDP checks with live observation/download evidence in specs/037-early-accurate-publication/verification.md.

## Documentation and release

- [x] T014 Update affected publication/replay/export contracts, README.md, TECH_DETAILS.md and docs/current-contracts.md; validate Markdown/links/examples.
- [x] T015 Update canonical corp-skills clearml-yolo usage/evaluation references and validate its package; record companion commit/evidence.
- [ ] T016 Obtain fresh independent integrated review, reconcile task delta against other agents' finished changes and validate architecture acceptance.
- [x] T017 Follow docs/development.md commit procedure and complete sequential Git-only release after other agents finish; verify pushed refs.

## Dependencies and execution

T001 → T002 → T003. Configuration T004–T006 and publication T007–T010 may proceed
in parallel with disjoint ownership after the interface contract. T011–T015 depend on
implementation; T016 follows integrated checks/docs; T017 requires acceptance and release
coordination. Deliver the full requested change; no partial MVP release.

## Resumed delivery — 2026-10-19

- [x] R001 Recover the feature after prerequisite 036 in isolation and verify clean application against concurrent changes.
- [x] R002 Re-run real CPU controller cache and paired pipeline publication/download checks; preserve scheduler coverage as an explicit gap.
- [x] R003 Complete integrated hooks, separate architecture checks and fresh independent review.
- [x] R004 Release the application through the native Git-tag workflow, then release the portable skill sequentially.

Fresh integrated source review and reconciliation passed. T016 remains open only
for the architecture acceptance failure caused by the declared scheduler gap;
T013 remains incomplete for that execution coverage. The user renewed Git-only
release authorization with the limitation disclosed.

Application v0.35.0 and companion v0.2.10 were released sequentially and remote
refs verified. T013 and the acceptance portion of T016 remain open solely for
actual scheduler execution; all other listed implementation/review/delivery work
is complete. See the final dated verification for evidence and limitations.
