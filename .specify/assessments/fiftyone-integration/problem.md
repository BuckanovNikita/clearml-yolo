# Problem Definition: FiftyOne Integration

- **Slug**: fiftyone-integration
- **Created**: 2026-09-29
- **Inputs used**: intake.md, research.md, user requirements

## Problem Statement

Pipeline operators can calculate fixed-threshold metrics but cannot inspect the exact evaluated boxes and statuses per image in a persistent visual review surface. Adding that surface must not alter scoring, duplicate media, break task ownership, or force an optional runtime dependency onto disabled runs.

## Affected Users & Stakeholders

- **Users**: ML operators and reviewers — need a reusable sample-level view of current results.
- **Stakeholders**: maintainers — must preserve package boundaries, existing entrypoints, artifacts, and deterministic evaluation contracts.

## Goals

- Make selected executions publish precise, reusable evaluated results.
- Preserve exact current-test/frozen-threshold evidence and output retention on failure.
- Keep disabled invocations free of FiftyOne imports and side effects.

## Non-Goals

- Replacing digital-metrics matching or using FiftyOne evaluation.
- Copying image media, launching a UI, publishing `cy-val`/`cy-compare`, or changing any of nine entrypoints.

## Success Metrics

- A completed eligible invocation has one owner receipt and reusable dataset/run completion evidence (baseline: unknown).
- Disabled eligible invocations import no FiftyOne module and create no FiftyOne state (baseline: unknown).
- Published labels reproduce digital-metrics TP/FP/FN/filtered outcomes and IoU for fixture cases (baseline: unknown).

## Cost of Inaction

Review remains split between CSVs, dashboards, and local image paths, making diagnosis slower and less directly auditable.

## Open Questions

- API behavior must be validated by a real FiftyOne smoke run before release.
