# Feature Specification: Stable ClearML parameter identity

**Created**: 2026-10-16
**Status**: Approved for implementation
**Input**: Exclude execution-only devices, names and temporary paths from experiment
parameters without breaking ClearML pipeline caching. Preserve full replay settings;
GPU indices may differ, but device types and counts remain significant.

## User Scenarios & Testing

### User Story 1 — Compare meaningful settings (Priority: P1)

An experiment author sees scientific settings without run-specific routing noise.
Publication must not change the settings actually executed.

**Independent test**: Native owner callbacks and detector argument publication omit
execution-only fields while preserving model, optimizer and dataset semantics.

### User Story 2 — Reuse equivalent pipeline steps (Priority: P1)

A controller can reuse completed work when GPU indices, task names or generated
output/cache roots change. Scientific changes invalidate reuse.

**Independent test**: The installed ClearML hashing path produces equal keys for
equivalent execution variants and different keys for semantic changes.

### User Story 3 — Replay complete settings (Priority: P1)

The author can clone a task without losing the real requested device or native
settings. Scientific General overrides remain effective and output routing remains fresh.

**Independent test**: Local and remote configuration tests retain full settings,
explicit empty values, credential redaction and existing precedence.

### Edge cases

Automatic device selection, unknown fields/documents and unproven input paths remain
cache-sensitive. Class names and model selectors are semantic. Unknown/malformed
configuration must never be silently erased to create a cache match. Cache hits reuse
existing task outputs; they do not recreate files at new local destinations.
ClearML project names remain semantic when used for fallback model selection.
Pipeline run roots remain semantic when skipped stages consume existing files.
JSON whose escape semantics differ from the SDK replay parser stays unnormalized.

## Requirements

- **FR-001**: Filter known native execution-only hyperparameters before publication.
- **FR-002**: Retain sanitized complete replay settings without mutating executable inputs.
- **FR-003**: Provide explicit controller-side cache normalization before lookup.
- **FR-004**: Ignore GPU indices while retaining device type/count and unresolved selectors.
- **FR-005**: Preserve scientific settings, code/container identity and unknown content.
- **FR-006**: Normalize generated dataset paths only with recorded existing cache identity.
- **FR-007**: Preserve owner/DDP publication, model/artifact and failure contracts.
- **FR-008**: Provide documented registration, verification and Git-only delivery.

## Success Criteria

- Equivalent GPU allocations `[0,1]` and `[2,3]` share cache identity.
- Changes to device count/type, data/model identity or scientific settings do not collide.
- Native execution and remote replay use original values, never cache placeholders.
- Real CPU publication and cache-hit/miss evidence accompany isolated regression checks.

## Assumptions

The external controller opts into the helper. Historical tasks are not rewritten.
Existing input immutability and dataset fingerprint contracts remain unchanged.
No dependency upgrades, GPU scheduling changes or new pipeline runner are included.
