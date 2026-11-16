# Ticket99 verification selection — 2026-11-16

Base product source: `137079d099490e2153405f042befe8325e9a38bc`.
Documentation-only successors through `0e1d039` do not change this baseline.
This routine correction implements feature014 FR-006/SC-004. See the
[captured diagnosis](2026-11-16-memory-basis-diagnosis.md).

## Change and selected checks

The two runtime modules now retain explicit NVML free bytes, preserve raw NVML
unavailable bytes and CUDA profile totals, and express returned unavailable bytes
relative to the selected CUDA capacity. The allocator uses the lower of CUDA and
explicit NVML free readings. The direct native harness consumes the same basis.
Existing ownership, UUID, timeout and missing-telemetry checks remain applicable.
When NVML free exceeds CUDA capacity, capacity-relative availability saturates at
that capacity; this remains conservative rather than claiming extra CUDA space.

- **Passed:** captured inventory regression failed before correction and passed
  after it. Allocator regressions exposed both directions of total disagreement;
  two failed before correction and all three parametrizations passed afterward.
- **Passed:**254 focused product tests in7.98 seconds cover inventory, allocator,
  training ownership, native probe and batch-estimation behavior.
- **Passed:** mypy on all six affected files; Ruff checking and format checking.
- **Pending:** native automatic gate on the integrated committed content, scoped
  mutation analysis and fresh independent review.
- **Deferred until integration/review:** new live DEIMv2 S JSON capacity/training
  and independent publication/readback. Original failed cases remain failed.

Exact checked hashes and red/green logs are retained in
`.tmp/ticket99-count-fix/verification.json`. CPU tests inject CUDA/NVML boundary
readings; they do not establish physical allocation or publication outcomes.
No new global coverage-floor claim is selected for this localized correction.
Previously accepted full-suite coverage remains historical evidence at its own
recorded inputs; the scoped suite does not replace it with a new count or floor.

## Queue compatibility and reusable evidence

Read-only inspection of clean cy-queue revision
`d3627a0da85968429ddeaff4920c05825e6e05e2` found no import of CY's private
`GPUState`, `gpu_states` or inventory/reserve modules. Queue startup occupancy uses
its own NVML adapter. No dependency, package metadata, public queue-consumed
interface or queue policy changes in this patch. Under the native acceptance
checklist, a new full paired suite is therefore not selected for this narrow fix.
The earlier paired result remains explicitly historical, not a new pass.

Campaign-only queue instrumentation did consume the mixed-basis subtraction. Its
original inputs and failed receipts were archived unchanged; a separate v2 child
observer uses explicit `state.free_bytes`. That v2 preparation is not runnable or
accepted until source/profile applicability and package/snapshot identities are
refreshed after this correction. The previous queue admission cannot be reused as
confirmed capacity or relabelled as successful execution.

Boundary inspection and exact archive hashes remain under
`.tmp/verification-gap-closure/ticket92-plan-v2-20261116/`. The final integrated
diff must remain within this stated scope for the pairing decision to apply.
