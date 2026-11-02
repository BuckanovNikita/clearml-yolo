# Bug assessment: align automatic batch search to eight

- Slug: `batch-align-eight` (generated from the requested fix).
- Date: 2026-11-02.
- Source: user request to align automatic batch searches to 8 and release.
- Verdict: valid policy gap; medium severity. No measured speedup is claimed.

## Observation and cause

Current default `memory_guided_v1` starts at batch 1 and refines in individual
images, allowing unaligned results such as 11. NVIDIA alignment guidance supports
trying aligned dimensions but does not establish a universal speed penalty.
The requested policy is an eight-image per-GPU grid, including distributed core
searches, with explicit numeric training batches unchanged.

## Remediation

Add versioned `memory_guided_aligned_v1` as the default. Preserve both old strategy
algorithms and their keys for replay. New search starts at eight per GPU, rounds
ceilings down, grows and refines on the grid, and freshly confirms its winner.
A ceiling below eight per GPU is invalid; OOM/budget failure at eight is
`no_capacity`. Numerical failure confirms only the prior aligned success.
Reject unaligned historical results for automatic lookup without rewriting evidence
or claiming a rounded, unmeasured batch. Schema 3 already records explicit strategies.

Core owns all policy without effects. Application, CLI, GPU probing, persistence
and explicit training arguments keep existing ownership and interfaces. See
[architecture.json](architecture.json). Python compatibility and dependencies stay
unchanged. Use the latest released source in an isolated checkout to preserve the
original dirty workspace. Release target is the next patch after 0.44.6.

## Tasks and acceptance

1. Add a failing original-path regression and grid/ceiling/failure/replay tests.
2. Implement the versioned policy and compatible automatic selection.
3. Update affected tests, batch guide, README, active feature contracts and portable
   usage guidance; validate Markdown, links and examples.
4. Run focused regressions, canonical verification (including import negatives and
   CPU-DDP), documentation checks and latest paired CY/queue normal resolution.
   Mutation scope excludes batch estimation; no performance or native GPU claim.
5. Obtain fresh independent review, reconcile the complete diff, validate architecture,
   and commit/tag/push through native release hooks. Preserve other changes.

## Files and risks

Change `src/clearml_yolo/core/batch_estimation.py`, affected batch tests, the batch
contract/docs and this task's evidence. Old unaligned recommendations require fresh
measurement; low-memory models may need explicit batches below eight. Neither
rounding old evidence nor fallback to unaligned automatic values is permitted.
