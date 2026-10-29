# Tasks: local Russian documentation

## Setup and foundations

- [x] T001 Inspect baseline/contracts and preserve 007 work in specs/008-local-docs/plan.md.
- [x] T002 Validate module decisions in specs/008-local-docs/architecture.json.
- [x] T003 Capture command/model/profile and parser baseline in tests/fixtures/docs-compatibility.json.
- [x] T004 Add shared typed documentation records in src/clearml_yolo/core/documentation.py.

## US1: complete reference

- [x] T005 [US1] Add documented named command/utility declarations and compatibility projection in src/clearml_yolo/entrypoints/hydra/declarations.py and option helper.
- [x] T006 [US1] Document existing Pydantic public configuration fields at their owning definitions.
- [x] T007 [US1] Document supported native settings in src/clearml_yolo/entrypoints/documentation/native.py.
- [x] T008 [US1] Assemble catalog/defaults and fail-closed coverage in src/clearml_yolo/entrypoints/documentation/catalog.py.
- [x] T009 [US1] Verify composition/export/replay/parser compatibility in tests/test_docs_compatibility.py.

## US2: safe local editing

- [x] T010 [US2] Test and implement isolated bounded previews in src/clearml_yolo/entrypoints/documentation/preview.py and adapters/documentation/worker.py.
- [x] T011 [P] [US2] Implement loopback HTTP/assets/process ownership in src/clearml_yolo/adapters/documentation/server.py.
- [x] T012 [P] [US2] Implement accessible search/editor/diffs/copy/download UI in src/clearml_yolo/adapters/documentation/assets/.
- [x] T013 [US2] Add cy-docs CLI and package entrypoint in src/clearml_yolo/entrypoints/docs.py and pyproject.toml.
- [x] T014 [US2] Enforce imports and injected failure isolation in .importlinter and tests/test_docs_isolation.py.
- [x] T015 [US2] Verify keyboard/offline/error/shutdown browser behavior in browser_tests/.

## US3: Russian learning paths

- [x] T016 [P] [US3] Author all required scenarios and inventory in src/clearml_yolo/adapters/documentation/assets/tutorials/.
- [x] T017 [US3] Render Markdown and check packaged links/examples via scripts/render_docs.py and documentation checks.

## Documentation update and acceptance

- [x] T018 Update README.md, docs/current-contracts.md, docs/project-contracts.md and docs/local-documentation.md.
- [x] T019 Update and verify portable corp-skills clearml-yolo guidance/evaluation cases; record in evidence/documentation.md.
- [x] T020 Run canonical verification, cy-docs --check and docs checks; record evidence/verification.md.
- [x] T021 Verify separate source installation and native YOLO/non-YOLO pipelines/artifacts; record evidence/native.md.
- [x] T022 Obtain fresh independent final review, reconcile actual diff and validate architecture acceptance.
- [ ] T023 Complete paired CY/cy-queue checks and authorized Git-only release, recording exact delivery state.

## Dependencies and parallelism

T001–T004 precede implementation. T005–T009 establish reference compatibility. Typed catalog
and preview interfaces permit disjoint browser, server and tutorial work; parent integrates
before T014–T015/T017. T018–T021 precede fresh T022 review and T023 delivery. Each public
requirement FR-001–010 and success criterion SC-001–005 maps to these phases; missing
required checks remain open tasks, never successful acceptance. No subagent delegates.

## Acceptance outcome — 2026-10-29

Implementation, documentation, native evidence, separate source installation and
fresh independent review are complete; see [verification](evidence/verification.md)
and [review](evidence/review.md). The companion portable guidance has a task-scoped
source commit. T023 remains open: preserved feature 007 acceptance must be settled
before CY commit/release, and the intended final version pair must then be verified.
No broader scope or release approval is inferred from the pending user choice.
See [delivery boundary](evidence/delivery.md).

## Authorized release resumption — 2026-10-29

The later explicit commit/push/release request authorizes T023. Fetched source
history confirms 007 already shipped as 0.42.0; integrate 008 into that accepted
baseline, retain its fixes, and verify CY 0.43.0 with the intended queue version.
The earlier acceptance outcome above is a historical checkpoint. See the
[updated delivery record](evidence/delivery.md#authorized-release-resumption).
