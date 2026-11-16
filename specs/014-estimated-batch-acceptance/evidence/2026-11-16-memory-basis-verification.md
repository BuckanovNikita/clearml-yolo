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
- **Passed:** initial254 focused product tests in7.98 seconds covered inventory,
  allocator, training ownership, native probe and batch-estimation behavior.
  After mutation-led strengthening,260 focused tests passed in8.38 seconds.
- **Passed:** mypy on all six affected files; Ruff checking and format checking.
- **Passed:** native automatic gate on clean integrated commit `8b7b4b3`.
- **Passed:** mutation-led tests exercise the actual isolated metadata script
  using a child-only fake CUDA boundary, captured subprocess failures, bounded
  timeout/reaping, idle delays and the allocator cap under separately sampled
  free/reserved readings. Nine targeted fault substitutions all failed their
  associated tests. These remain controlled CPU observations, not GPU execution.
- **Passed:** full offline coverage on clean `b3a8bd8`:4813 passed,1 skipped,
  536 warnings in339.74 seconds;84.81% exceeds the84.12% floor. This includes the
  ordinary CPU-DDP suite but establishes no physical multi-GPU result.
- **Passed with triage:** the second scoped mutation run produced214 killed and19
  surviving mutants, with none unrun/unreached or excluded by budget. Survivors
  comprise14 diagnostic-presentation changes,3 integer-domain equivalents and2
  bounded timing margins. The timing margins are not claimed equivalent: a
  30-to31-second metadata timeout and an extra poll at exact idle-deadline equality
  retain the bounded policy. The original174 killed/59 survivors report remains
  unchanged; its substantive gaps motivated the strengthened tests.
- **Passed:** canonical automatic gate exited0 on clean `ba2b984`; independent
  reviewer `count_review` verified the complete integrated diff, check evidence,
  native consistency and raw/normalized artifact links with no outstanding findings.
  This approves the offline correction for separately admitted serial native validation.
- **Passed live execution/readback and independent evidence review:** new DEIMv2 S
  JSON case `deimv2-s-json-22b56424f0` freshly confirmed batch24 and completed two
  epochs with14 optimizer updates. Native ownership cleanup passed; all459 launcher
  source inputs remained unchanged. The207 supplemental samples reached a minimum
  of10347 MiB free, with a maximum1.177-second sample gap; they do not establish a
  continuous measured minimum. The native reserve guard also passed throughout.
  Independent remote readback and CPU prediction passed; original failed cases
  remain failed.

Exact checked hashes and red/green logs are retained in
`.tmp/ticket99-count-fix/verification.json`. CPU tests inject CUDA/NVML boundary
readings; they do not establish physical allocation or publication outcomes.
The strengthening receipt is
`.tmp/ticket99-count-fix/strengthening/verification.json`, SHA-256
`da792993242a5592ae2532c61bc6f7cc830ae1f756fd5fbb22dc84c2b87db473`.
Actual preformat snapshots were committed as `93680d2`; independently reproduced
automatic fixes/formatting were committed separately as `b3a8bd8`. Both final test
files match the focused-check receipt. Product source remains identical to `8b7b4b3`.
Before live validation, all537 tracked source/test paths in the root working tree
were compared with clean `ba2b984` and matched exactly. Root HEAD `0e1d039` alone
does not identify the uncommitted correction. The separate prelive identity receipt
and launcher source manifest establish the executed inputs. Independent reviewer
`count_review` approved T018 after checking all129 protected file hashes and the
removal of exactly197,970,881 duplicate logical bytes. The original failed case's
seven retained diagnosis files remain unchanged. See the
[ticket09 execution/readback evidence](../../000-baseline/evidence/2026-11-16-ticket09-deim-json.md).
No selected correction check remains deferred; final evidence-only reconciliation
uses the canonical automatic gate before local main integration. No push or release
is part of this acceptance.

Full offline coverage is selected because the corrected runtime is shared across
backends. Previously accepted full-suite coverage remains historical evidence at
its own recorded inputs; the focused suite does not replace it with a new count
or floor. The new full run uses clean committed `b3a8bd8`, four pytest workers,
two numerical-library threads and hidden CUDA devices.
The retained full-suite log is `2026-11-16-memory-basis-coverage.log`; the final
native mutation report is `2026-11-16-memory-basis-mutation-final.json`, SHA-256
`251e4f93b4aad58fb01c1a991eda56d87c07564313bcce6a47f53cba823e6e6b`.
Native mutation excludes the decorated `GPUState.used_for` method. Its two manual
fault proofs remain applicable because the method bytes and all three relevant
test ASTs (seven cases) are unchanged. No tooling policy or source transformation
was introduced to claim native mutation coverage of this excluded method.

Native hygiene removed trailing whitespace in two captured manual-fault logs in
the separate mechanical commit `6560160`. The unchanged JSON reports' original
`log_sha256` values bind raw blobs retained in `d665668`; current normalized hashes
and exact Git object names are recorded in
`2026-11-16-memory-basis-log-normalization.json`. All other mutation artifacts remain
byte-identical. No failure text or outcome was altered.

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
observer uses explicit `state.free_bytes`. The independently reviewed v2 candidate
pins refreshed source/profile and package/snapshot identities; its manifest SHA-256
is `684fc100919c686a56386ba96e93ccfff4a0c43f76625242bb535e529058ed38`.
All23 files and351 source hashes were checked. Only the two corrected product
modules differ from v1; the scientific recipe and dependencies remain unchanged.
Launch still requires final correction checks/review and a serial GPU slot.
The previous queue admission cannot be reused as
confirmed capacity or relabelled as successful execution.

Boundary inspection and exact archive hashes remain under
`.tmp/verification-gap-closure/ticket92-plan-v2-20261116/`. The final integrated
diff must remain within this stated scope for the pairing decision to apply.
