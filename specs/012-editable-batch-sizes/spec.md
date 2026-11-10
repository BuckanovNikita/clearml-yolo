# Feature Specification: Editable batch sizes and small-batch discovery

**Feature Branch**: `012-editable-batch-sizes`
**Created**: 2026-11-10
**Status**: Approved intent
**Input**: Implement the supplied “Simplify batch estimation and discover small batches” plan.

## User Scenarios & Testing

### User Story 1 - Edit training batch recommendations (Priority: P1)

A training operator edits a readable table and uses `batch=null` across datasets and recipes.
**Why this priority**: Operators need direct control over recommendations without altering measurement evidence.
**Independent Test**: Edit an entry to 3 and resolve training on one and multiple GPUs.
**Acceptance Scenarios**:
1. Given an exact hardware/model/square-size entry, lookup uses it regardless of classes, density, recipe, augmentation or dependencies.
2. Given no exact entry, lookup selects the largest capacity no greater than the target, breaking ties by smallest batch then GPU name, and warns with source and estimation command.
3. Given mixed GPUs, resolve each independently and multiply the smallest batch by GPU count.
4. Given a manual exact entry and a previous no-capacity marker, the manual entry wins.

### User Story 2 - Discover capacity below eight (Priority: P1)

An operator measures a model that fits fewer than eight images.
**Why this priority**: Large models otherwise have no usable automatic recommendation.
**Independent Test**: Simulate each capacity zero through eight and low ceilings.
**Acceptance Scenarios**:
1. Start at eight when permitted; after capacity failure search integer batches one through seven; above eight retain the multiples-of-eight grid.
2. Independently confirm every winner; only OOM or budget excess at one establishes no capacity.
3. Preserve distinct numerical recovery, timeout, cancellation and infrastructure outcomes and historical replay/keys.

### User Story 3 - Refresh safely and inspect offline (Priority: P2)

An operator refreshes selected measurements without losing unrelated edits or valid values on interruption.
**Why this priority**: Measurements are expensive and manual configuration must remain trustworthy.
**Independent Test**: Inject failed receipts, concurrency, malformed tables and interrupted refresh.
**Acceptance Scenarios**:
1. Explicit models or refresh forces fresh measurement; otherwise preserve exact entries and measure missing combinations, optionally populating from compatible evidence.
2. Parent acceptance, successful exit and owned cleanup precede publication. Fresh results replace historical values; competing eligible results use the smallest confirmed batch.
3. No capacity removes exact entry and blocks fallback; later success clears failure. Other unsuccessful refreshes preserve entries and report failure.
4. Offline listing reports table coverage and known failures without CUDA.

### Edge Cases

Precise capacities near readable-label rounding boundaries; manual literal capacities; equal-capacity ties; invalid/duplicate YAML; concurrent writers; low ceilings; nonfinite confirmation; unsupported model/device/non-square requests; no JSON fallback in training.

## Requirements

### Functional Requirements

- **FR-001**: Make `CY_HOME/.config/clearml-yolo/batch-sizes.yaml` authoritative for automatic training batch lookup; accept positive integer per-GPU values under GPU/size/canonical model keys.
- **FR-002**: Preserve precise measured capacities internally; interpret manual labels literally absent metadata.
- **FR-003**: Resolve exact first, then lower/equal-capacity fallback with deterministic ties and source warning.
- **FR-004**: Preserve explicit batches, existing device/model/shape restrictions and normal OOM failure behavior; no automatic retries.
- **FR-005**: Record table digest, selected entries, fallback sources and batches without claiming manual/fallback values were measured on the target.
- **FR-006**: Measure 150 classes always, remove `--classes`, retain density default 300 and other controls.
- **FR-007**: Version new search without changing historical replay or keys; confirm all winners independently.
- **FR-008**: Retain strict internal cache compatibility and readable JSON evidence; never silently substitute JSON for training lookup.
- **FR-009**: Apply freshness, failure-marker and publication semantics in story 3, with locked atomic updates preserving comments/unrelated entries and rejecting malformed content without overwrite.
- **FR-010**: Update contract, CLI guidance and Russian README; verify search, selection, refresh, storage and integration behavior plus project acceptance.

### Key Entities

- Table entry: source GPU name/capacity, square size, canonical model, positive per-GPU batch.
- Selection: target GPU, selected entry, exact/fallback origin and table digest.
- Measurement: strict profile/workload/settings and independently confirmed trial evidence.
- Failure marker: exact hardware/model/size combination where batch one failed capacity.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every simulated capacity from zero through eight yields the expected confirmed recommendation or explicit no-capacity result.
- **SC-002**: Manual edits are honored across datasets with classes below and above 150 and changed recipes.
- **SC-003**: Every rejected receipt or unsuccessful refresh preserves prior table values; concurrent updates preserve unrelated entries/comments.
- **SC-004**: Historical fixture replay and keys remain unchanged; offline listing requires no GPU.

## Assumptions

Hardware fallback is a recommendation, never proof of capacity on target hardware. Existing supervision, resource ownership and explicit release authorization remain in force. Push authorization is absent.
