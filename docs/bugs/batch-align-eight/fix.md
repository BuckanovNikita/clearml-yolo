# Bug fix: aligned automatic batch search

- Slug: `batch-align-eight`, reused from the assessment.
- Date: 2026-11-02.
- Assessment: [assessment.md](assessment.md).
- Status: applied; behavior, documentation and independent review accepted.

## Implementation

Core now defaults to `memory_guided_aligned_v1`. It starts at eight images per GPU,
rounds ceilings and predictions down, advances by at least eight, binary-refines
on the same grid and independently confirms the winner. A ceiling below eight per
GPU raises an explicit error; capacity failure at eight yields `no_capacity`.
Other failures and numerical recovery retain the full existing evidence checks.
The two older strategies and source-key serialization remain unchanged.
Automatic compatibility rejects an unaligned historical per-GPU winner without
rewriting the case or inventing a measured rounded batch. Explicit native batches
and all GPU/SDK/storage effect ownership remain unchanged.

The new original-path regression failed before implementation: expected next batch
8, observed 1. Grid tests cover one through four ranks, capacities around boundaries,
nonaligned ceilings, guided jumps, binary refinement, numerical recovery, rejected
confirmation and historical lookup. Existing integration fixture capacities now
satisfy the policy; historical sequence tests select their original strategy.

## Documentation and scope

Updated the batch contract, Russian README, current contract navigation, active
feature spec/data model/interfaces and append-only follow-up tasks. The portable
usage source and queue fixture companion are maintained in separate isolated clones.
No changes to dependencies, numerical computation, memory budgets, native trainers,
queue runtime behavior or physical performance claims are included.

## Deviations

The remote baseline was newer than the original dirty local checkout. Work uses
latest released 0.44.6 in an independent clone, preserving all original changes.
Schema 3 already records explicit strategies; no additional schema bump is needed.
