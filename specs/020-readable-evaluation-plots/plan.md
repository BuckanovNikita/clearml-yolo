# Implementation Plan: Readable evaluation plots

## Summary
Apply the approved current-model-only display policy at publication boundaries. Render
one class-series PR chart on test and one selectable confusion chart per split.

## Technical Context
Python 3.12, existing ClearML adapter and plain Plotly dictionaries; no new dependency.
Keep result/model schemas and durable CSV identities stable. Invocation-local display
slots use checkpoint hash when available, then model ID, then context identity; split
is always part of the key. Repeat publications reuse the slot. Collisions append a
readable stage and ordinal, with no hash suffix. Unknown display identity is Current model.

## Constitution Check
Typed Python, existing import boundaries, pinned dependencies and one-task ownership
remain. No upstream edits. Required checks are pytest, Ruff, mypy and import-linter.
Documentation and native publication verification are explicit acceptance gates.

## Structure and Implementation
- Interactive rendering and comparison table removal: clearml_report adapter.
- Baseline exclusion and display-slot allocation: clearml_results publication boundary;
  optional keyword-only display label on rendering functions preserves direct callers.
- Native PR filter: project native callback adapter, also used by DDP owner replay.
- Full identifiers remain in CSVs/workbooks/provenance, removed from chart captions only.

## Verification
Focused behavior tests precede changes. Run repository checks and a small isolated real
pipeline with baseline. Inspect actual SDK events and browser legend/selector interaction.
Run fresh independent read-only review after parent verification.

## Documentation Stage
Amend specs/014-evaluation-publication/contracts/publication.md and interfaces.md,
specs/019-model-report-identity/contracts/report-identity.md, native tracking contract,
docs/current-contracts.md, relevant README passages and project E2E guidance.
Validate Markdown, local links and changed examples. Keep dated evidence separate.
