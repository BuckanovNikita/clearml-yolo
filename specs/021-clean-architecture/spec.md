# Feature Specification: Clean architecture and Pandera

**Feature Branch**: `021-clean-architecture`
**Created**: 2026-10-08
**Status**: Approved for implementation
**Input**: Implement the reviewed full package redesign, clean Python-path cutover, scientific core, and Pandera dataset validation.

## User Scenarios & Testing

### US1 — Enforced architecture (P1)
A maintainer adds a module or dependency and receives an actionable architecture failure for an unclassified module, cycle, SDK escape, or reversed dependency. Test the actual graph and injected hypothetical imports.

### US2 — Unchanged execution (P1)
A user runs existing command names with regenerated YAML and receives the same dataset, predictions, evaluation, reporting and tracking behavior. Verify standalone and composed execution, failures and current-data comparison.

### US3 — Explicit validation (P1)
A dataset user receives consistent structured validation while retaining source IDs and existing recoverable invalid-box filtering. Test Pandera schemas against accepted/rejected existing fixtures.

### Edge Cases
Numeric/Unicode labels; blank background rows; repeated boxes and headers; conflicting image/split identity; invalid finite/ordering/bounds geometry; preserved raw predictions; optional publication failure; failed required uploads; cancelled GPU jobs; dynamic worker and plugin targets.

## Requirements

- **FR-001**: Organize all runtime modules into core, application, adapters and entrypoints, plus the shipped Hydra plugin root. Enforce inward dependencies, exhaustive classification, acyclic helpers and SDK ownership.
- **FR-002**: Application workflows depend on explicit typed ports and project-owned requests/results; the entrypoint composition root constructs adapters. No SDK/Hydra objects cross into core.
- **FR-003**: Core allows standard library, Pydantic, Pandera, pandas, NumPy and SciPy; no filesystem/network/process effects, SDK imports or adapter dependencies.
- **FR-004**: Use Pandera dataframe schemas with no implicit coercion, row dropping or extra-column filtering. Preserve existing parsing, row lineage, structural failures, dropped-box diagnostics and stage-specific geometry policies.
- **FR-005**: Preserve CLI names, config fields, native defaults, output formats, thresholds, matching/AP/statistical algorithms, task ownership and required failure behavior.
- **FR-006**: Separate evaluation computation from rendering/publication and identity models from persistence. Retain digital-metrics/report-generator approved sources without changes.
- **FR-007**: Remove old Python paths, update all callers/runtime targets/resources, document regenerated YAML without runtime legacy translation, and keep package imports inert.
- **FR-008**: Preserve GPU queue and native/DDP semantics, explicit resource ownership, optional FiftyOne behavior, and explicit task tags/project names.
- **FR-009**: Update constitution narrowly for new architecture/validation roles, maintained documentation and links; record dated verification and complete independent review and release gates.

## Key Entities
Typed command requests, application ports, dataset validation findings, model identity, computed evaluation, evaluation artifacts, publication request/receipt, invocation and resource ownership.

## Success Criteria
- **SC-001**: All intended imports pass and all forbidden/cycle/unclassified-module negative tests fail as designed.
- **SC-002**: Existing observable tests retain outcomes; new schema, injection, import-purity and dynamic-target checks pass.
- **SC-003**: Required real CPU/GPU, publication/download and comparison acceptance has dated evidence; unavailable gates remain explicitly unverified.
- **SC-004**: Documentation, package builds/installs, ten command helps and regenerated configuration examples pass validation.

## Assumptions
Clean cutover and YAML regeneration are explicitly approved. Pydantic remains for records/config; Pandera handles dataframe validation. Only Pandera and its necessary direct/transitive requirements may change dependencies. No deployment, upstream patching or registry publication.
