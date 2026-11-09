---
description: "Task list for the identity footer feature"
---

# Tasks: Identity Footer for Excel Reports

**Input**: Design documents from `specs/010-identity-footer/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/interfaces.md](contracts/interfaces.md)

**Tests**: Required by constitution IV (observable behavior and contracts). Each story
writes its tests first.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Record baseline: run `uv run pytest tests/test_v2_workbook.py` in `external/report-generator` and `uv run --frozen --no-sync pytest tests/test_workbook_identity.py tests/test_shared_extraction_compatibility.py`, and note results in this ledger.

## Phase 2: Foundational

- [x] T002 Add frozen `IdentityLinks(model_url: str | None = None, task_url: str | None = None)` with `extra="forbid"` and the rule "Absolute `http`/`https` URL, or None" in `src/clearml_yolo/core/identity.py`, with tests in `tests/test_identity_flows.py`.
- [x] T003 Add `TrackingSession.identity_links`, the `links` keyword on `ReportRenderer.annotate_workbook`/`write_evaluation_workbook` and on `EvaluationWriter.render_evaluation` per contracts/interfaces.md in `src/clearml_yolo/application/ports.py`. Update the fakes in `tests/workflow_dependencies.py`.

## Phase 3: User Story 1 - Tables start at the top (P1) 🎯 MVP

**Goal**: No banner rows above data. One identity footer below all content, including drawings.
**Independent Test**: Every worksheet's header is in row 1, cells are unchanged, and the footer starts at last used row/anchor + 2.

- [x] T004 [US1] Upstream tests for `placement="bottom"` in `external/report-generator/tests/test_v2_workbook.py`:
  - coordinates, formulas, defined names and charts are unchanged;
  - start row covers drawing anchors;
  - an empty sheet starts at row 2;
  - empty `banner_lines` produces metadata only;
  - print area is extended;
  - no Print_Titles;
  - byte-exact `original_workbook`;
  - idempotent re-annotation;
  - `"top"` with new kwargs raises.
- [x] T005 [US1] Implement bottom placement in `external/report-generator/report_generator/v2/workbook.py` (R1, R2). The prepend path must stay untouched. Run the full upstream suite, then commit in the report-generator repo (Conventional Commit).
- [x] T006 [US1] Tests in `tests/test_workbook_identity.py`:
  - replace the prepend-shift test with a footer-layout test;
  - an aliased workbook with identity gets one contiguous footer that includes the alias notice;
  - an aliased workbook without identity gets an alias-only footer;
  - a historical top-banner workbook still recovers and re-annotates into the footer layout.
- [x] T007 [US1] Implement footer lines and single-block envelopes (R3) in `src/clearml_yolo/adapters/reporting/workbook_identity.py`: `_footer_lines`, metadata-only presentation envelope when identities exist, and `placement="bottom"`.
- [x] T008 [US1] Update the expectation transform in `tests/test_shared_extraction_compatibility.py` to the footer layout, keeping original-recovery equality.

## Phase 4: User Story 2 - ClearML links (P2)

**Goal**: Model and training-task lines link to ClearML; plain text otherwise.
**Independent Test**: Injected links appear as hyperlinks. Without links, plain lines appear and no identifier is visible.

- [x] T009 [US2] Upstream tests and implementation of `banner_links` in `external/report-generator/tests/test_v2_workbook.py` and `report_generator/v2/workbook.py`:
  - external hyperlink relationships;
  - length mismatch and non-http(s) URLs raise.
  Commit separately in report-generator.
- [x] T010 [P] [US2] Add `src/clearml_yolo/adapters/clearml/links.py`. `identity_links` returns empty links with no SDK call when `Task.current_task()` is None. Otherwise it builds the task URL with `Task.get_task_output_log_web_page(task_id)` and the model URL as `<Session.get_app_server_host()>/projects/*/models/<id>`. Failures are logged at DEBUG and return empty links. Tests go in `tests/test_clearml_models.py`, using substitutes for the SDK.
- [x] T011 [US2] Footer link mapping per data-model.md in `src/clearml_yolo/adapters/reporting/workbook_identity.py`. Forward `links` through `src/clearml_yolo/adapters/reporting/evaluation.py` and `evaluation_workbook.py`.
- [x] T012 [US2] Resolve and pass links in `src/clearml_yolo/application/evaluation.py`, `application/use_cases/metrics.py`, `compare.py` and `report.py`. Never resolve links for the reporting task. Wire them in `src/clearml_yolo/entrypoints/composition.py`.
- [x] T013 [US2] Flow tests in `tests/test_evaluation_identity.py`, `tests/test_report.py` and `tests/test_identity_flows.py`:
  - hyperlinks on paired comparison roles;
  - plain fallback;
  - no visible task/model identifier or digest.

## Phase 5: User Story 3 - Printed pages identify the model (P3)

**Goal**: A page footer on every annotated worksheet.
**Independent Test**: `oddFooter` holds the escaped role/name/status text, ≤255 characters.

- [x] T014 [US3] Upstream `page_footer` tests and implementation (R4): `&` escaping, the 255-character truncation rule, and preservation of other existing headerFooter sections. Files: `external/report-generator/tests/test_v2_workbook.py`, `report_generator/v2/workbook.py`.
- [x] T015 [US3] Build the page footer text in `src/clearml_yolo/adapters/reporting/workbook_identity.py`, with tests in `tests/test_workbook_identity.py`: long Unicode names and formula-like labels.

## Phase 6: Polish & Cross-Cutting

- [x] T016 Bump the approved report-generator revision in `docs/development.md`. Pin the release as the minimum version.
- [x] T017 [P] Update the contracts:
  - `docs/readable-output.md` and `docs/shared-evaluation-reporting.md`: footer, links, page footer, naive-reader note;
  - `specs/000-baseline/spec.md`: replace the print-title requirement;
  - `docs/current-contracts.md` index;
  - README.md (Russian) if it describes banners.
- [x] T018 Run `ruff check .`, `mypy .`, `lint-imports` and `uv run --frozen --no-sync pytest --testmon-noselect`.
- [ ] T019 Live stand check per quickstart.md, including the model-page URL form (R5 open check). Clean up tagged objects.
- [x] T020 Independent review of the integrated diff (CY and report-generator). Address the findings.
- [x] T021 Commit CY changes per the commit procedure, run `prek run --all-files`, reconcile this ledger, and evaluate the release workflow.

## Dependencies

- T002–T003 come before all stories.
- US1 (T004–T008) comes before US2 and US3: both extend the bottom-placement code.
- In US2, T010 can run in parallel with T009/T011. T012 depends on T010/T011.
- US3 depends only on US1.
- Polish runs after all stories, in the order T016/T017 → T018 → T019 → T020 → T021.

## Parallel Examples

- US2: T010 (ClearML adapter) alongside T009 (upstream links).
- Polish: T017 docs alongside T016.

## Implementation Strategy

Build the MVP (US1) first: headers back in row 1 with a plain footer. Then add links
(US2) and the page footer (US3). Upstream changes land as separate report-generator
commits before the CY revision bump.

## Ledger

- 2026-11-09: spec, plan and tasks created.
- 2026-11-09 T001 baseline: upstream `tests/test_v2_workbook.py` 12 passed; CY workbook identity + compatibility 29 passed.
- 2026-11-09 T005/T009/T014 landed together as report-generator `9199c4f` (cohesive single API change); review fix `d1a14aa` widens only the final print area to the merged footer width; `f3dff38` restores fit-to-width printing (full-suite regression in `test_report_class_availability`). Both commits are local and unpushed: fresh clones cannot fetch the approved revision until report-generator is pushed (needs separate authorization).
- 2026-11-09 T010 deviation: `identity_links(task, identity)` takes the invocation task (no SDK call when None) instead of `Task.current_task()`; it also suppresses a training-task link equal to the reporting task (FR-008 single-task pipelines, review finding).
- 2026-11-09 T020 independent review: no high-severity findings; fixed FR-008 self-link and print-area width/multi-area; accepted residual: drawing-height estimate uses default row height, and `humanize_workbook` re-annotation of an already annotated workbook renders without links (no current caller).
- 2026-11-09 T019 partial live check on the shared stand (tag clearml-yolo-claude-20261109-links-529n, CPU only, cleaned: 0 projects/tasks/models left): `identity_links` built `https://clearml.k8s.docker.internal/projects/*/experiments/<id>/output/log` (SDK chose the `experiments` route for this server API) and `.../projects/*/models/<id>` for a real task and output model, and suppressed the self link. Not verified: browser rendering of the model route (no browser tool in this session) and a full GPU train→compare→report run producing linked workbooks.
- 2026-11-09 T018: first full suite exposed 6 regressions (test fakes without `links`, lost fit-to-width print setup), fixed; rerun 4170 passed with 1 compatibility expectation updated for fit-to-width, then that module 18 passed. ruff, mypy (440 files), lint-imports (16 kept) clean.
- 2026-11-09 T021: commits `f746094` (spec) and `2e3e55a` (feature); final `prek run --all-files` result recorded below. Release evaluation: no version tag cut (push and report-generator publication not authorized; approved revision is local-only).
- Remaining T019 gap: browser check of the model page route and a full GPU run producing linked workbooks.
- 2026-11-09 T021 final gate before delivery: `prek run --all-files` at `99d5c3c` exited 0 (13 hooks).
- 2026-11-09 delivery (user-authorized push and report-generator release): report-generator `chore(release): 0.2.0` `7339ef8` fast-forwarded `main` from `d10aa39` with annotated tag `v0.2.0` and GitHub release; upstream suite 184 passed, ruff clean. This supersedes the local-only notes above. CY pins `report-generator>=0.2.0`, the lock records 0.2.0 and the approved revision is `7339ef8`. Paired check: CY 0.46.2 (master, this commit series) with cy-queue 0.1.9 `cd85a0c` (origin/main, fetched): editable install of report-generator, CY and queue, `uv pip check` compatible, installed report-generator 0.2.0, queue suite 528 passed (7 deselected), `cy-queue --help`, queue lint-imports (2 kept), ruff and mypy clean. No CY version tag: the `feat` would release 0.47.0, outside cy-queue's `clearml-yolo>=0.38,<0.47`.
