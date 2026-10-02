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
