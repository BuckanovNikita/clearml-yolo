# Tasks: Configuration examples and 0.3.0 publication

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), and [CLI contract](contracts/cli.md).

This is the completed historical ledger for v0.3.0. Checked tasks are backed by repository
inspection or dated evidence. The
[native configuration feature](../003-ultralytics-config-groups/spec.md) later superseded sparse
native settings and expanded initializer output to include two native group files; those
changes do not reopen these tasks.

## Phase 1: Setup

- [x] T001 Inspect current code, history, instructions, and release state in `pyproject.toml` and `specs/001-release-030/`.
- [x] T002 Capture user outcomes and decisions in `specs/002-config-init-release/spec.md` and `research.md`.

## Phase 2: Governing Contracts

- [x] T003 Amend `.specify/memory/constitution.md` for explicit annotations and local configuration initialization.
- [x] T004 Define destination, example, and publication contracts in `specs/002-config-init-release/contracts/cli.md` and `data-model.md`.

## Phase 3: US1 - Editable Examples

**Independent test**: Installed initializer creates eight examples; all compose; collision,
force, symlink, and directory checks preserve user data.

- [x] T005 [US1] Reproduce the missing installed entrypoint and add behavioral coverage in `tests/test_config_tree.py`.
- [x] T006 [US1] Implement central-default export and destination checks in `src/clearml_yolo/config_tree.py`.
- [x] T007 [US1] Restore argparse entrypoint in `src/clearml_yolo/apps/config_tree.py` and script/import contracts in `pyproject.toml`.
- [x] T008 [US1] Update `README.md`, `docs/migration-030.md`, `AGENTS.md`, and `specs/001-release-030/contracts/cli.md`.

## Phase 4: US2 - Explicit Annotations

**Independent test**: No first-party prohibited imports; test collection, validation,
configuration composition, and strict static checks pass.

- [x] T009 [US2] Remove future-annotations imports throughout `src/clearml_yolo/` and `tests/`, and remove their requirement from `pyproject.toml`.
- [x] T010 [US2] Preserve self-reference typing in `src/clearml_yolo/clearml_session.py`, `src/clearml_yolo/tasks/compare.py`, and `tests/test_inference.py`.
- [x] T011 [US2] Reproduce and repair runtime pandas generic annotations in `src/clearml_yolo/clearml_report.py` and `src/clearml_yolo/comparison/reinfer.py`.
- [x] T012 [US2] Run the complete test suite and strict checks configured in `pyproject.toml`.

## Phase 5: US3 - Verified Publication

**Independent test**: Downloadable packages install separately, expose nine commands, and
match the checksums attached to the release's pushed source commit.

- [x] T013 [US3] Complete specification, plan, decisions, models, validation guide, and checklist under `specs/002-config-init-release/`.
- [x] T014 [US3] Validate package installation, nine command helps, and generated examples for both distributions; record results in `docs/evidence/2026-09-28-release-030.md`.
- [x] T015 [US3] Verify isolated live CPU/GPU paths and artifact retrieval using `.agents/skills/running-end-to-end-tests/SKILL.md`; record current outcomes and limitations in `docs/evidence/2026-09-28-release-030.md`.
- [x] T016 [US3] Record cross-artifact consistency review in `specs/002-config-init-release/analysis.md` and release notes in `docs/releases/0.3.0.md`.
- [x] T017 [US3] Pass all `.pre-commit-config.yaml` gates and commit/push explicit task-owned source, test, and documentation paths.
- [x] T018 [US3] Publish `v0.3.0` with verified distributions and checksums from the task's build directory; verify remote tag and downloaded assets against `docs/releases/0.3.0.md`.

## Phase 6: Approved Concurrent Changes

- [x] T019 [US3] Include pinned `external/` gitlinks, `.gitmodules`, editable sources in `pyproject.toml` and `uv.lock`, dependency lint exclusions, and installation documentation in `README.md` and `AGENTS.md`.
- [x] T020 [US3] Consolidate `.agents/skills`, replace `.claude/skills` with a relative symlink, and reconcile host invocation and script-interface guidance.
- [x] T021 [US3] Verify submodule revisions, locked sync, fresh package installs using explicit Git sources, shared skill metadata/links, and Spec Kit script compatibility; record evidence.

## Dependencies and Execution

T001–T004 establish scope and governing contracts. US1 and US2 are independently testable;
US3 depends on both. Package verification and read-only documentation review can proceed
while isolated live verification runs. Publication follows successful final checks and push.

Within US1, tests preceded implementation. US2 reused existing tests and repaired observed
collection failures. The working tree retains all authorized changes without stashing or
resetting. The minimal deliverable was US1; the user's later requests added US2 and US3.

Parallel examples, with separate ownership: review US1 examples while checking US2 annotation
imports; review US3 documents while package installation runs. Git writes and publication
remain serialized under one owner. T019–T021 reflect the user-approved scope expansion
and must complete before T017–T018.
