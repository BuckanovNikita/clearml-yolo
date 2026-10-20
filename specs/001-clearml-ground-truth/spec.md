# ClearML ground truth and complete default installation

**Status**: Approved for implementation on 2026-10-20.

## Baseline and feature identity

This feature amends the [stage-zero specification](../000-baseline/spec.md) for
ground-truth source selection and default runtime dependencies. Its original
`036-clearml-ground-truth` records moved to `001-clearml-ground-truth` in the new
numbering epoch after concurrent baseline integration. Requirements and completed
history are preserved; the [task ledger](tasks.md#concurrent-baseline-integration--2026-10-20)
tracks the renewed integration and delivery gates.

## User scenarios and testing

### US1 — Consume versioned annotations (P1)

Users select a ClearML dataset by ID or project/name with an optional version.
The root `dataset.csv` supplies annotations, while images remain external.
Acceptance covers both selectors, omitted versions, unchanged CSV contents and
existing image-path interpretation across standalone and composed commands.

### US2 — Preserve local inputs with guidance (P1)

Users can still execute with local CSV paths and receive one warning per invocation
recommending a ClearML dataset. Internally produced paths do not trigger warnings.
Help, configuration inspection and queue submission do not fetch datasets.

### US3 — Install all supported runtime dependencies (P1)

A default installation includes the former queue UI, detector and export extras.
Declared lower bounds have passing evidence on supported Python minors; development
tools remain separate. Existing external runtime prerequisites remain explicit.

## Requirements

- FR-001: Accept a dataset ID or a project/name pair with optional version; reject
  incomplete, mixed, empty or unknown selector fields.
- FR-002: Consume finalized datasets containing only root `dataset.csv`, rejecting
  additional files or links before materialization, using ClearML version
  selection when the version is omitted. Never create a dataset on a failed lookup.
- FR-003: Preserve source bytes and image references. Relative image paths remain
  relative to the downloaded CSV; no image upload, remapping or conversion is added.
- FR-004: Resolve once in each invocation, preserve the requested replay selector,
  and record resolved dataset identity, version and CSV digest separately.
- FR-005: Support all existing ground-truth consumers, queue snapshots and remote
  replay; retain local inputs with an execution warning and no eager SDK lookup.
- FR-006: Install all former runtime extras by default and retain upstream extras
  required by those dependencies. Keep development dependencies separate.
- FR-007: Establish tested direct runtime floors within existing constraints on
  Python 3.12.13 and 3.13; retain exact pins, upper bounds and approved sources.
- FR-008: Preserve the approved digital-metrics source, reference and locked revision.
- FR-009: Update current input/installation guidance and the portable usage skill;
  complete architecture, documentation, independent review and release gates.

## Success criteria

- SC-001: ID and project/name inputs consume the same CSV as their local equivalent.
- SC-002: Pipeline composition performs one lookup and emits no duplicate local warning.
- SC-003: A built wheel installs runtime capabilities without project extras on both
  supported Python minors; tested lower bounds and unavailable checks are recorded.
- SC-004: The final diff passes required checks and independent review before release.

## Assumptions and exclusions

The user chose mappings under `ground_truth`, root `dataset.csv`, existing image-path
rules, and oldest tested versions rather than blanket lock-version floors. Version
is valid only with project/name because an ID already identifies a dataset version.
Unversioned selectors resolve again on a later invocation. No image-root option,
YOLO dataset conversion, upstream source changes, deployment or registry publishing
is included. TensorRT system prerequisites and DEIM source checkouts remain external.
ClearML owns archive transfer and caching; selective materialization does not promise
that historical archive chunks contain no bytes from subsequently removed files.
