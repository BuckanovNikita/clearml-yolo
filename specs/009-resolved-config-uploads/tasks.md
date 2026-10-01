# Tasks: Resolved configuration uploads

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [configuration-files.md](contracts/configuration-files.md)

> **Current-contract note:** Checked tasks preserve completed feature and release history.
> Consumed configuration files are now stored as Configuration Objects and never duplicated as
> artifacts. Task phrases such as "uploaded configuration files" and "downloaded-file
> verification" describe the original implementation target and acceptance evidence.
> See [current contracts](../../docs/current-contracts.md).

**Tests**: Required behavioral regression tests precede implementation. Checkboxes record completed work only after acceptance evidence is available.

## Phase 1: Setup

- [x] T001 Inspect publication surfaces, module boundaries, current changes and governing contracts; record findings in specs/009-resolved-config-uploads/research.md (root and read-only subagents).
- [x] T002 Create and clarify specs/009-resolved-config-uploads/spec.md and checklists/requirements.md using user-approved decisions (documentation agent).
- [x] T003 Produce specs/009-resolved-config-uploads/plan.md, research.md, data-model.md, contracts/configuration-files.md and quickstart.md; complete Constitution Checks (documentation agent).

## Phase 2: Foundation

- [x] T004 Lock injected resolver signatures and exclusive implementation ownership in specs/009-resolved-config-uploads/plan.md (root).
- [x] T005 Generate traceable tasks and perform read-only cross-artifact analysis in specs/009-resolved-config-uploads/analysis.md (documentation agent).

## Phase 3: User Story 1 - Replay uploaded configuration files

**Goal**: Uploaded active values are resolved against source-local and effective command context with preserved types/comments.

**Independent test**: Inspect the actual configuration path submitted to the publication boundary, including current command values after replay/routing changes.

- [x] T006 [P] [US1] Add failing resolver regressions covering nested mappings/lists, typed values, nulls, file root whole-key precedence, original-field projection and strict resolver failures in tests/test_config_resolution.py (resolver agent; FR-001–003, FR-006).
- [x] T007 [P] [US1] Add failing YAML/JSON attachment regressions covering file-local references, active values versus comments, source preservation and replay-returned files in tests/test_clearml_session.py (attachment agent; FR-001–003, FR-005–006).
- [x] T008 [US1] Implement typed strict resolution in src/clearml_yolo/apps/config_resolution.py and deferred shared CLI callback in src/clearml_yolo/apps/common.py (resolver agent; FR-002–003, FR-008–009).
- [x] T009 [US1] Inject and retain the optional resolver callback and apply strict preparation before publication in src/clearml_yolo/clearml_session.py without Hydra/OmegaConf imports (attachment agent; FR-001–003, FR-006, FR-009).
- [x] T010 [US1] Add and run integrated shared-command/publication tests proving current replay/routing context in tests/test_release_config.py or the existing affected integration test module (root; FR-008).

## Phase 4: User Story 2 - Preserve private execution inputs

**Goal**: Publication resolves before sanitization while execution retains usable unredacted data and original files remain unchanged.

**Independent test**: Compare source, returned execution and uploaded copy bytes using a credential-bearing resolver fixture.

- [x] T011 [US2] Add failing tests for resolve-before-sanitize, separate execution/upload copies, returned replay inputs and original-path behavior without interpolation in tests/test_clearml_session.py (attachment agent; FR-004–007).
- [x] T012 [US2] Implement comment-preserving resolved execution copies and sanitized upload copies in src/clearml_yolo/clearml_session.py; retain existing no-interpolation return behavior (attachment agent; FR-004–007).
- [x] T013 [US2] Integrate resolver/attachment changes and inspect failure handling and credential leakage across the combined diff in src/clearml_yolo/clearml_session.py and src/clearml_yolo/apps/common.py (root; FR-004–009).

## Phase 5: Verification, convergence and release

- [x] T014 Run affected tests and repository pytest/Ruff/mypy/import gates, documenting actual results in specs/009-resolved-config-uploads/verification-2026-09-30.md (root; SC-001–004).
- [x] T015 Run real ClearML downloaded-file verification and required release CPU/single-GPU native evidence using project/environment skills; record owned resources and limitations in specs/009-resolved-config-uploads/verification-2026-09-30.md (root; SC-005).
- [x] T016 Independently review implementation and run speckit-converge against specs/009-resolved-config-uploads artifacts; append and implement gaps until converged (root/reviewer and documentation agent).
- [x] T017 Validate feature Markdown/links and run applicable pre-commit gates; review/stage only explicit task-owned paths, then create the authorized Conventional Commit using scripts/local_release.py documented hooks (root; verification document records results).
- [x] T018 Verify semantic-release version commit/tag, push authorized commits/tags, publish/verify GitHub release and wheel/sdist assets, and record release evidence in specs/009-resolved-config-uploads/verification-2026-09-30.md (root).

## Dependencies and parallel execution

T001–T005 establish shared intent and interfaces. T006 and T007 may run concurrently under exclusive test ownership. T008 depends on T006; T009 depends on T007 and the locked interface. T010 follows integrated T008/T009. Attachment agent executes T011 before T012 without another writer in its files. T013 follows T008/T009/T012. T014–T018 follow combined implementation, with verification/review before release. Documentation agent alone updates feature tasks/evidence after receiving results.

## Implementation strategy

Ship US1 resolution and publication correctness first, then establish US2 execution/privacy guarantees before final verification. Root integrates subagent deliverables and executes shared checks; reviewers remain read-only for product code. Do not claim native or remote publication success from mocked tests. Preserve unrelated work and existing shared resources. Commit and release only after the authorized checks pass.

## Phase 6: Convergence

Initial implementation ran before this assessment. Independent review identified three P1 gaps despite the passing initial suite. The following tasks capture remaining behavior; original completed task markers describe initial execution, not final acceptance. Existing verification/release tasks remain pending and are not duplicated.

- [x] T019 [US2] Preserve credential provenance from sensitive command-context values and sensitive environment references through innocuous aliases, using frozen ResolvedConfigFile metadata and configuration_secrets; add regression tests in src/clearml_yolo/apps/config_resolution.py, src/clearml_yolo/clearml_session.py and their exclusively owned test modules (resolver/attachment agents; FR-004, FR-011; constitution credential protection).
- [x] T020 [US1] Remove artificial markers from registered resolver arguments while preserving escaped literals/direct aliases; add exact-argument regressions in src/clearml_yolo/apps/config_resolution.py and tests/test_config_resolution.py (resolver agent; FR-002, FR-010).
- [x] T021 [US1] Normalize and strictly validate tuple resolver outputs and reject resolver-emitted active interpolation; add nested sequence/error regressions in src/clearml_yolo/apps/config_resolution.py and tests/test_config_resolution.py (resolver agent; FR-001, FR-006, FR-010).
- [x] T022 [US2] Preserve relative-path semantics by placing unique resolved execution copies beside the source and cleaning only owned files; test lifecycle cleanup in src/clearml_yolo/clearml_session.py and tests/test_clearml_session.py (attachment agent; FR-005, FR-009).

> **Supersession note (2026-10-01):** T022 records the completed design at that time. The current
> filesystem contract moves owned execution copies to `CY_HOME/.tmp`; rootless native dataset YAML
> receives its source parent only in the execution copy so relative paths remain valid. See
> [filesystem ownership](../../docs/filesystem-policy.md) and
> [feature 011](../011-workspace-filesystem/spec.md). The historical completion marker remains
> unchanged.

T019–T022 precede final T014–T018 acceptance. Resolver and attachment writers retain exclusive ownership; root coordinates the shared frozen-result interface and reruns integration/live checks.

## Phase 7: Convergence

Supplemental independent review exposed additional resolution gaps. Existing final verification/release tasks remain pending.

- [x] T023 [US2] Inventory the exact sensitive value consumed by embedded custom-resolver references without reevaluating noncached resolvers and leaking a different value; add no-cache probe regression for an embedded sensitive command alias in src/clearml_yolo/apps/config_resolution.py and tests/test_config_resolution.py (resolver agent; FR-004, FR-011; constitution credential protection).
- [x] T024 [US1] Reject unsupported set/object resolver outputs recursively with safe diagnostics before publication in src/clearml_yolo/apps/config_resolution.py and tests/test_config_resolution.py (resolver agent; FR-001, FR-006, FR-010).
- [x] T025 [US1] Preserve mixed escaped literals plus active interpolation and embedded aliases without changing literal text or overlooking active references in src/clearml_yolo/apps/config_resolution.py and tests/test_config_resolution.py (resolver agent; FR-002, FR-010).

T023–T025 precede final verification, independent review and converged acceptance in T014–T018. Their tests must capture the supplemental failing observations before fixes.

## Phase 8: Convergence

Final independent review reproduced credential leakage through dynamically computed node targets, which have no safe provenance without reevaluating custom resolvers.

- [x] T026 [US2] Reject dynamic node references such as `${${key}}` confidentially before publication; add direct/embedded regressions and distinguish supported nested resolver arguments in src/clearml_yolo/apps/config_resolution.py, tests/test_config_resolution.py and the feature contract (root; FR-004, FR-006, FR-011; contradicts; Constitution III credential protection).
