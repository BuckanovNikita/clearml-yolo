# Tasks: README quickstart

## Phase 1 — Setup and foundation

- [x] T001 Inspect README.md, docs/current-contracts.md, configuration and dependency evidence.
- [x] T002 Record approved requirements and plan in specs/016-readme-quickstart/.

## Phase 2 — US1: primary journey

Independent acceptance: configuration examples resolve and the reader can locate results.

- [x] T003 [US1] Rewrite setup, conversion, cy invocation and results in README.md.

## Phase 3 — US2: migration and discovery

Independent acceptance: tables cover the manual stages, parameter mapping and nine commands.

- [x] T004 [US2] Add migration tables, Mermaid diagram and auxiliary guidance in README.md.

## Phase 4 — Documentation update and validation

- [x] T005 Reconcile docs/development.md references and review retained contract destinations.
- [x] T006 Validate README.md and changed documentation; record dated results in specs/016-readme-quickstart/verification-2026-10-06.md.
- [x] T007 Obtain independent review of the complete diff and record its outcome in specs/016-readme-quickstart/verification-2026-10-06.md.

## Dependencies and implementation strategy

T001/T002 precede T003; T004 follows T003 because both own README.md. T005 and T006
follow the rewrite; T007 follows parent validation. A read-only investigation runs in
parallel with parent artifact preparation; agents own no writes. Deliver US1 first,
then US2, then validate the combined documentation. All FR-001 through FR-006 are
covered by T003 through T007; no application tests or new runtime contracts are needed.

## Phase 5 — User follow-up and documentation validation

- [x] T008 [US1] Make README.md start with existing ground_truth CSV; remove conversion from quickstart and diagram.
- [x] T009 [US2] Edit Russian prose in README.md and replace hardware/manual device advice with DDP, queue and automatic -1 examples.
- [x] T012 [US1] Remove the source-overrides block from README.md; validate frozen-lock setup and reconcile docs/development.md and specs/001-release-030/quickstart.md.
- [x] T010 Validate changed Markdown, links, diagram and single-device/DDP configurations; append evidence to specs/016-readme-quickstart/verification-2026-10-06.md.
- [x] T011 Obtain independent read-only review and record acceptance in specs/016-readme-quickstart/verification-2026-10-06.md.

T008, T009 and T012 share README ownership and precede T010; T011 follows parent validation.
The follow-up requirements are fully covered without changing the runtime contract.

## Phase 6 — Baseline inference clarification

- [x] T013 [US2] Explain fresh baseline inference and metrics on the current ground_truth test split in README.md.
- [x] T015 [US2] Describe FiftyOne visual inspection and shared metrics in README.md without enable/disable controls.
- [x] T014 Validate the documentation against comparison code, check Markdown/links and obtain independent review; append evidence to specs/016-readme-quickstart/verification-2026-10-06.md.

T014 follows T013 and T015. Existing weights and frozen thresholds remain unchanged.

## Phase 7 — Installation excerpt removal

- [x] T016 Remove general setup material from README.md, show direct cy commands, renumber steps, repair setup references in docs/development.md and the 001 quickstart, and validate documentation with independent review.
- [x] T017 Add and verify README.md's cy-config generation, native-parameter YAML examples and exact cy launch command; include the result in final independent review.

## Phase 8 — Primary YAML workflow and requested minor release

- [x] T018 [US1] Promote generated YAML setup/launch in README.md, remove the competing inline workflow and align DDP guidance.
- [x] T019 Validate README.md snippets, overrides, DDP composition, Markdown and links; record independent review in specs/016-readme-quickstart/verification-2026-10-06.md.
- [x] T020 Commit the accepted documentation and publish minor Git release 0.17.0 using repository release gates, without changing dependency revisions or publishing package assets.

T019 follows T018; T020 follows accepted review and required release checks.

## Phase 9 — Training-first README and technical reference (2026-10-15)

- [x] T021 Inspect current README, commands, configuration, model definitions and portable usage skill; establish the content-migration map and no-impact architecture record.
- [x] T022 Rewrite README.md in Russian with four training one-liners, everyday controls, full experiment and actionable independent workflows.
- [x] T023 Create English TECH_DETAILS.md, reconcile all migrated topics, navigation and incoming anchors, and correct encountered stale direct-GPU guidance.
- [x] T024 Validate Markdown, links/anchors, shell/YAML/Mermaid, resolved Hydra and temporary generated YAML examples; inspect queue help without workloads.
- [x] T025 Obtain fresh independent completeness/accuracy/language/separation review after integration and validation; reconcile actual diff and validate architecture acceptance.
- [x] T026 Record dated evidence, complete the documentation commit and native release evaluation/delivery without forcing a version bump.

T021 precedes T022/T023. A read-only command audit may accompany parent drafting;
T024 follows integration, T025 follows checks, T026 follows acceptance. Parent owns
all writes; bounded reviewers do not delegate. Completed phases above are historical.

## Phase 10 — Requested master landing (2026-10-15)

- [x] T027 Integrate current master, retain its Python compatibility and queue diagnostics, validate/review the documentation-only result, and land/push master through the native release workflow.
