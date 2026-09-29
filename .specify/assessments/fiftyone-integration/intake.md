# Idea Intake: FiftyOne Integration

- **Slug**: fiftyone-integration
- **Created**: 2026-09-29
- **Source**: pasted text and repository codebase
- **Type**: new-capability

## Idea (as captured)

> Add a default-enabled FiftyOne publication capability for `cy`, `cy-predict`, and
> `cy-metrics`. It must preserve current evaluation semantics, reuse local imports,
> keep images in place, retain ClearML task ownership, and be optional through a
> dependency-free no-op path.

## Restated

Record selected pipeline, prediction, and metrics results in a local persistent
visual-review dataset without changing model scoring or making the feature mandatory at runtime.

## Origin & Context

- **Raised by**: project user
- **Trigger**: need to inspect exact fixed-threshold evaluation outcomes alongside existing artifacts.

## First-Glance Unknowns

- Whether existing matching output retains enough identity for a faithful visual review payload.
- How completed imports and interrupted publication are distinguished safely.
- How the optional dependency remains absent from the disabled import path.
