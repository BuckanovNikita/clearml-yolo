# Implementation Plan: Remove legacy compatibility

**Branch**: `012-remove-legacy-compatibility` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved current-only contracts: CSV training, current Output Model and
validation CSV recovery, one evaluation configuration, strict input validation and canonical
cache settings. Remove migration documentation and synchronize maintained requirements.

## Technical Context

- Python 3.12, existing uv/Hydra/hydra-zen/Pydantic/Ultralytics/ClearML toolchain.
- Filesystem dataset caches and run outputs; ClearML owns remote publication.
- Pytest, Ruff, strict mypy and import-linter remain the executable gates.
- No dependency revision change, commit, push, deployment or existing-data deletion.
- No performance change is intended; native execution and source ownership must be preserved.

## Constitution Check

Constitution 6.0.0 implements the explicitly approved governance amendment before code work.
All other typing, dependency, privacy, single-task, publication and verification rules remain.
Pre-design and post-design checks pass: no unresolved scope decisions or required exceptions.

## Project Structure and Ownership

- Training agent: `tasks/train.py`, `native_dataset.py` and their exclusive tests.
- Recovery agent: `clearml_models.py`, `artifact_names.py`, `tests/test_clearml_models.py`.
- Parent: configuration, prediction-helper callers, comparison, filesystem, identity helpers,
  resolved-configuration copying, integration tests, import contracts and final verification.
- Documentation agent: README, maintained contracts/specifications, quickstarts and integration
  guidance; parent owns constitution, feature artifacts and combined consistency checks.
- Independent review: read-only inspection after parent verification.

## Documentation Update

Update README, project summary/index, filesystem policy, current contracts and active specs
for features 001, 003-ultralytics, 004, 005, 007, 008, 010 and 011. Remove the three migration
guides and repair their links, including release/history references. Preserve dated evidence
and completed task/research history. Update project-owned end-to-end guidance and the global
clearml-yolo environment examples. Validate changed Markdown and local links.

## Verification

Test changed rejection paths before implementation, then preserve current-path coverage.
Run focused tests, the full suite and all static gates. Real isolated CPU/GPU runs cover
CSV cache reuse, source immutability, baseline/candidate comparison, current model/threshold
downloads and owner publication. Record actual outcomes and unavailable gates in dated evidence.

## Workflow Adaptation

Completion authorization on 2026-10-02 adds full repository hook verification, commit and push
on this feature branch after review. The earlier implementation-only restrictions above record
the original scope. Dependency pins and local source overrides remain protected; no release or
merge is requested.

Ruling: use explicit feature context with read-only prerequisite resolution and authored
template-derived artifacts instead of setup helpers that persist `.specify/feature.json`.
Initial authorization under `.specify/` covered only the constitution. The completion instruction
also authorizes the proposed one-line historical link repair in
`.specify/bugs/excel-match-export/test.md`. No installed tooling or feature pointer is changed.
Existing local dependency overrides remain in place.

## Recovery compatibility plan amendment (2026-10-05)

Implement only the approved [specification amendment](spec.md#approved-recovery-compatibility-amendment-2026-10-05)
and [task recovery contract](contracts/task-recovery.md). Reuse the existing feature directory
and append tasks instead of rewriting completed work or the protected feature pointer.
`.specify/extensions.yml` contains no hooks; read-only prerequisite discovery resolves 012.
No setup helper, installed skill, constitution, dependency revision, commit or deployment changes.

### Design and ownership

- Recovery implementation owner: `clearml_models.py`, `artifact_names.py` and focused recovery
  tests. Normalize the supported threshold payloads with class-string/precision preservation;
  choose a checkpoint once and carry typed source identity to both weights and provenance.
- Parent: integration in comparison/configuration consumers and their tests; final repository
  checks, current-image inference acceptance, task-owned native resources and cleanup.
- Documentation owner: README, project summary/index, affected recovery contracts, active
  spec annotations/quickstarts and appended 012 design/task artifacts. No code ownership.
- Independent review: fresh read-only review after parent verification. Agents do not delegate.

### Constitution check and scope ruling

The historical constitution explicitly prohibits recovery alternatives. This conflicts with
AR-001–AR-004 and is surfaced rather than reported as a passing unmodified governance check.
The user expressly approved the compatibility plan and preservation of `.specify/`; that
instruction supersedes the recovery-only prohibition for this task. Other governance
constraints, native publication, CSV training and strict configuration rules remain intact.

### Verification and documentation update

Focused tests cover representations, ordered selection, absent versus malformed sources,
strict class/value validation, numeric-looking class names, precision, dashboard warnings,
ambiguous model metadata/basenames, last-model logging, artifact order, selected-only downloads,
`.pt` validation and source identity. Comparison tests cover explicit-map authority, frozen
thresholds, shared current image membership, no historical configuration/prediction import
and both source positions. Run affected static gates and the appropriate regression suite.
Use real tagged ClearML recovery/current-image inference when feasible; report architecture
compatibility and unavailable native gates without substituting mock outcomes.

Update README, `docs/project-contracts.md`, `docs/current-contracts.md`, contracts for 001/008/010/012,
active recovery specification annotations and quickstarts. Current publication remains one
native best model and full-precision validation CSV. Validate Markdown/local links, confirm
unchanged CLI syntax, and record dated acceptance only after parent evidence. Documentation
completion depends on inspecting the actual recovery/integration diff.
