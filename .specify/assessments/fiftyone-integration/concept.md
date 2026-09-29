# Concept: FiftyOne Integration

- **Slug**: fiftyone-integration
- **Created**: 2026-09-29
- **Recommended option**: typed neutral publisher with FiftyOne adapter

## Options

### Option A — Typed neutral publisher with FiftyOne adapter
- **Sketch**: Eligible commands create a neutral evaluation payload and send it to a replaceable publisher; the adapter maintains local datasets and namespaced run fields.
- **Appetite**: medium
- **Trade-offs**: preserves scoring and permits a no-op path, but needs careful identity, recovery, and adapter tests.
- **Rabbit holes**: dataset migration, database conflicts, and incorrect mapping after GT normalization.

### Option B — Direct FiftyOne calls inside each command
- **Sketch**: Each eligible command writes its own visual-review records.
- **Appetite**: small
- **Trade-offs**: initially direct, but duplicates ownership and risks leaking the dependency throughout the pipeline.
- **Rabbit holes**: divergent retry and completion behavior.

### Option C — Do nothing
- **Sketch**: Continue using existing CSV/dashboard artifacts.
- **Appetite**: small
- **Trade-offs**: no integration risk, but no sample-level persistent visual review.
- **Rabbit holes**: none.

## Recommendation

Choose Option A because it meets visual-review value while preserving the existing scoring authority, import boundaries, and single-task ownership requirements.

## Out of Scope (for the recommended option)

- UI launch, media copying, scoring changes, external dependency patches, and standalone val/compare publishing.

## Assumptions to Validate

- Local FiftyOne can reference resolved existing media paths and retain fields required by the payload schema.
- Dataset and run completion markers can support safe reuse and retry under a local lock.
