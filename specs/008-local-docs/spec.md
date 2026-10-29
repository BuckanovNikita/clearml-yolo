# Feature Specification: Local Russian configuration reference

**Feature**: 008-local-docs
**Created**: 2026-10-29
**Status**: Implementation accepted; authorized 0.43.0 release verification in progress
**Baseline**: [Stage zero](../000-baseline/spec.md)

## User Scenarios & Testing

### User Story 1 — Find and understand settings (P1)

After normal installation, a Russian-speaking user runs `cy-docs`, searches a field,
filters by command/model and follows a stable link to its meaning, accepted inputs,
constraints, defaults, applicability, examples and owning definition.

Acceptance: every public command option, configuration field and supported native setting
is described; effective defaults match command/model/profile composition. Inherited
expressions and selected values are shown separately. Generated provenance is identified.

### User Story 2 — Edit and preview configurations (P1)

A user edits named YAML documents and ordered overrides, previews their composition,
inspects differences and errors, then copies or downloads YAML and a terminal command.

Acceptance: preview cannot train, instantiate targets, load augmentation files or inspect
datasets. Environment/custom resolver expressions remain unresolved; external search paths
and plugin replacement are rejected before composition. Sweeps are bounded to 100 jobs
and workers to 15 seconds. Keyboard and offline use work.

### User Story 3 — Learn complete workflows in Russian (P2)

A user follows tutorials from installation and a small dataset through all model families,
training, evaluation, complete experiments, advanced composition, customization and operations.

Acceptance: every tutorial has prerequisites, editable examples, expected outputs, reference
links, common failures and verification instructions. A maintained scenario inventory links
every command and configuration group to reference, tutorial and verification cases.

### Edge cases

Missing assets, malformed tutorials and failed preview workers affect only documentation.
Nulls, missing required values, nested/list overrides, interpolation and dynamic mappings
remain representable. Shutdown reaps documentation-owned workers. Existing `007` changes
and saved configuration/replay contracts remain intact.

## Requirements

- **FR-001**: Provide local, offline, searchable Russian reference with stable field links
  and command/model filters, launched by `cy-docs` with port/browser/check controls.
- **FR-002**: Document public command and utility declarations, existing public configuration
  models and native settings without changing public locations or runtime validation.
- **FR-003**: Preserve keys, defaults, permissive composition, missing markers, interpolation,
  targets, exported YAML, replay payloads and parsing/help behavior against a captured baseline.
- **FR-004**: Show effective command/model/profile defaults, expression inheritance, dynamic
  inputs, inactive and wrapper-controlled values; exclude internal runtime records.
- **FR-005**: Provide bounded isolated composition previews with schema errors, unresolved
  values and deferred runtime checks, plus copy/download controls and differences.
- **FR-006**: Ship all assets and authored Russian tutorials; require no Node installation.
- **FR-007**: Cover installation/ClearML/data, training every family, prediction/validation/
  metrics/comparison/report/FiftyOne, full and partial pipelines/recovery, Hydra controls/DDP,
  augmentation and typed dependency customization, replay/queue/cache/weights/export operations.
- **FR-008**: Fail documentation verification for uncovered fields/options/groups, missing
  assets, invalid links or invalid tutorial configuration examples.
- **FR-009**: Enforce serving/effect ownership and isolation from core/application commands.
- **FR-010**: Verify compatibility, browser behavior, source installation, native YOLO and
  non-YOLO execution/artifacts, paired queue compatibility and fresh independent review before release.

## Key Entities

Field declaration; command declaration; effective configuration; named YAML document;
preview request/result; tutorial; scenario inventory. See [data model](data-model.md).

## Success Criteria

- **SC-001**: All supported public configuration and CLI inputs have complete Russian entries.
- **SC-002**: Existing configuration/replay/parser behavior passes the compatibility baseline.
- **SC-003**: Users can search, edit, preview and download entirely offline after installation.
- **SC-004**: Invalid or failed previews leave ordinary application commands usable.
- **SC-005**: Every required tutorial scenario is linked to an executable verification case.

## Assumptions and scope

Training remains terminal-driven. Queue guides use existing cy-queue interfaces; no queue
schema, arbitrary Hydra stage substitution or plugin API is introduced. Runtime validation
remains authoritative. The user explicitly requests implementation of the supplied plan;
its final planning-only sentence describes the prior turn, not this execution request.
