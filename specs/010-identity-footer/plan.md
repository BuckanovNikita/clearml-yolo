# Implementation Plan: Identity Footer for Excel Reports

**Branch**: `master` (Spec Kit feature directory `010-identity-footer`) | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-identity-footer/spec.md`

## Summary

Move visible model identity and the class-alias notice from prepended banner rows to an
identity footer below each worksheet's content. Model and training-task lines link to
ClearML web pages built at render time. A plain-text page footer replaces repeated print
titles. The generic OOXML mechanics come from an additive bottom-placement mode in
report-generator. clearml-yolo resolves links through a tracking port and passes plain
URLs to the reporting adapters ([research](research.md)).

## Technical Context

**Language/Version**: Python `>=3.12.13,<3.14`

**Primary Dependencies**: report-generator (local source under `external/`, additive change),
ClearML SDK (URL builders), openpyxl/pandas (existing)

**Storage**: xlsx artifacts (OOXML packages with embedded custom-XML envelopes)

**Testing**: pytest (CY and report-generator suites), ruff, mypy, lint-imports, prek

**Target Platform**: Linux (WSL2), shared Kubernetes ClearML stand for the live check

**Project Type**: Python library + Hydra CLI applications

**Performance Goals**: no measurable change. Link building is string formatting on an
existing session.

**Constraints**: byte-exact original recovery; no visible identifiers; no network call
without a live session; digital-metrics unchanged; existing prepend behavior unchanged

**Scale/Scope**: about 6 annotated workbook kinds, 4 application call sites, 1 upstream function

## Constitution Check

| Principle | Assessment |
| --- | --- |
| I. Typed, explicit Python | New `IdentityLinks` is a frozen Pydantic core model. All new functions are typed. The ClearML boundary catches failures and logs them at DEBUG, as the spec requires. PASS |
| II. Module boundaries | ClearML stays in `adapters/clearml`. Application use cases call `deps.tracking.identity_links` and pass plain data to the reporting ports. Core gains only a Pydantic model. Import-linter and architecture tests stay unchanged and must pass. PASS |
| III. Configuration and run ownership | No configuration surface changes. Links come from the invocation's own session and never point to the reporting task. PASS |
| IV. Verification | Product tests for layout, links, fallback, page footer, recovery and rejection. Upstream legacy tests unchanged. Full pytest, then prek. A live stand check for real links (mocked tests don't establish it). PASS |
| Dependency policy | The report-generator revision change is explicitly authorized by the user (2026-11-09). digital-metrics is untouched. PASS |

Re-checked after Phase 1 design: no violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/010-identity-footer/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/interfaces.md
└── tasks.md            # /speckit-tasks
```

### Source Code

```text
external/report-generator/report_generator/v2/workbook.py   # bottom placement, links, page footer
external/report-generator/tests/test_v2_workbook.py          # new bottom-mode tests
src/clearml_yolo/core/identity.py                            # IdentityLinks
src/clearml_yolo/application/ports.py                        # identity_links, links kwargs
src/clearml_yolo/application/evaluation.py                   # pass links to render_evaluation
src/clearml_yolo/application/use_cases/{metrics,compare,report}.py  # resolve + pass links
src/clearml_yolo/adapters/clearml/links.py                   # ClearML URL builders (new)
src/clearml_yolo/adapters/reporting/workbook_identity.py     # footer lines, single block, page footer
src/clearml_yolo/adapters/reporting/{evaluation,evaluation_workbook}.py  # forward links
src/clearml_yolo/entrypoints/composition.py                  # wire identity_links
tests/test_workbook_identity.py, tests/test_shared_extraction_compatibility.py,
tests/test_identity_flows.py, tests/test_evaluation_identity.py, tests/test_report.py,
tests/workflow_dependencies.py                               # contract updates + new cases
docs/readable-output.md, docs/shared-evaluation-reporting.md, docs/development.md,
specs/000-baseline/spec.md, docs/current-contracts.md, GLOSSARY.md
```

**Structure Decision**: Use the existing layered layout. One new adapter module
(`adapters/clearml/links.py`) keeps URL construction with the other ClearML SDK code.

## Delivery and authorization

Commits are local only and follow the commit procedure. The report-generator change is
committed in its own repository first. Then the CY revision bump points at that local
commit; fresh clones cannot reproduce it until it is pushed (push not authorized). Release
evaluation follows acceptance. The paired CY/queue release check applies only if a release
is cut.

## Complexity Tracking

None.
