# Batch search speedup verification, 2026-10-30

## Scope and isolation

Implementation starts from released CY 0.44.3,
`02e2d50ad9f3dd6ea619f69adfe5ffc45c32f361`, in an isolated checkout. The original
dirty checkout, its local uv sources and unrelated workloads remain intact. No
dependency recipe, optimizer path, validation requirement or native trial duration
was reduced. The proposed performance patch is 0.44.4.

The change adds memory-guided candidates, schema-3 strategy provenance and independent
model/hardware case processes. The parent publishes usable evidence only after a
matching receipt, successful exit and owned descendant cleanup. Compatible verified
cases are read from the persistent catalogue before worker admission; ordinary
relaunches neither repeat their trials nor require an idle GPU. Failed cases retry;
explicit refresh and changed compatibility inputs still require new measurement.

## Focused implementation checks

The new private-worker tests initially failed because the entrypoint did not exist;
the new CLI concurrency/resume tests exposed the serial implementation before
integration. After implementation:

- Search/storage/numerical checks passed 173 tests, with 125 adjacent regression
  tests also passing. Frozen schema-1/2 fixtures were captured from unchanged 0.44.3
  before implementation; expected historical key hashes are fixed independently.
- CLI, private case-worker and architecture checks passed 304 tests. Coverage
  includes automatic/one/two-job admission, compatible GPU affinity, ordered output,
  failed-peer retry, byte-preserving verified-case reuse and invalid receipt rejection.
- CLI, private case-worker and documentation compatibility checks passed 226 tests.
- Real pool subprocess tests passed, including overlapping cases, peer survival,
  detached descendants with a replaced trial marker, preservation of an unrelated
  helper, startup failure, uncertain-cleanup quarantine and repeated SIGINT/SIGTERM.
- Multiprocess catalogue writers preserved distinct cases under the existing lock
  and atomic replacement boundary. Search tests retain five warm-up and ten measured
  optimizer updates, all configured optimizer paths, validation and fresh confirmation.
- Scoped Ruff and strict mypy passed. Exhaustive import checking retained all 52
  contracts, including the new private entrypoint and forbidden pool dependencies.

Deterministic affine and nonlinear memory tests establish candidate selection and
exact measured boundaries. For the affine curve `100 + 10 × batch`, capacity 24
uses six full trials instead of eleven, and capacity 96 uses seven instead of
fifteen, including fresh confirmation in both strategies. These are synthetic-policy
results, not measurements of native runtime speed.
Numerically limited results retain their original failure and independent confirmation;
different candidate order can produce a different last successful recommendation.

## Canonical verification and documentation

Canonical application verification passed with receipt
`e3e8fd6a264943d48ed0950a0524d52f`: Ruff, strict mypy, Vulture, all 52 import
contracts and the full pytest suite passed. Pytest reported **4,571 passed,
30 skipped, 81 deselected and 178 warnings** in 1,136.61 seconds, including actual
CPU-DDP and subprocess lifecycle checks. Skipped/opt-in tests are not passes.
The verifier produced its unchanged-input success receipt after all commands exited
zero. Earlier attempts are not passes:
one identified a hardcoded test token (corrected to a generated token); another was
interrupted after detecting stale queue metadata in the copied environment. The
environment was corrected through normal dependency resolution with latest queue
0.1.5; `uv pip check` passed. Copied console entrypoints were relocated to the isolated
environment before the final run.

The documentation verifier passed before final evidence reconciliation. The changed
Russian README, maintained guides, active feature interfaces, shared CLI examples and
generated training tutorial were checked; 199 documentation/catalogue compatibility
tests passed. The documentation verifier also passed after review and evidence reconciliation.

Mutation applicability was inspected: configured targets are `core/datasets.py`,
`core/evaluation/policy.py` and `core/export_quality.py`, with their selected tests.
None is changed by this amendment, and their dependency pin is unchanged. No mutation
run was required or represented as passing.

## Native benchmark gap

A task-owned comparison harness uses the actual case-process command path for
`yolo11n` and `fcos/resnet50_fpn`, image size 320, four classes, 20 objects/image,
ceiling eight, one selected GPU and one job. It compares legacy and guided strategies
with identical full native settings and would then check an ordinary cached relaunch.
Its initial discovery/idle preflight exited 2 before any model ran:

```text
RuntimeError: GPU 0 is busy or its telemetry is unavailable
```

There are no native trial counts, timing comparisons or successful native cache-repeat
results from this attempt. A second attempt after canonical verification also failed the same idle preflight
before running models. The existing workload was preserved; no idle criterion was
relaxed. T041 and native speed acceptance remain open. Physical two-GPU execution is
also unverified; the user explicitly authorized release without that separate physical
check. CPU process overlap does not establish GPU scaling. The single-GPU benchmark
gap is separate from that exception.

## Paired sources, review and delivery

Current and proposed CY/queue checks are recorded in [paired evidence](paired.md);
both passed normal resolution and 518 queue tests. The unchanged latest queue 0.1.5
accepts CY 0.44.4. Portable usage checks are recorded in
[companion evidence](portable.md). [Fresh independent review](review.md) accepted the implementation with no unresolved
findings. Parent reconciliation and documentation checks passed; architecture acceptance
still fails because the native benchmark is unavailable. Final committed-pair refresh
remains pending. No release commit, tag or push has occurred at this checkpoint.

## Explicit delivery authorization, 2026-10-30

After disclosure of the two failed idle preflights and the separate single-GPU
benchmark gate, the user instructed **“push”**. This authorizes the Git-only 0.44.4
delivery with that benchmark gap recorded, in addition to the earlier physical
multi-GPU exception. It does not turn T041 or full architecture acceptance into
passes. Ordinary checks, independent review, final paired-source verification and
normal release hooks remain required; no native guarantee or idle criterion changes.

## Release hooks and queue follow-up

The normal hooks committed the batch implementation as
`80615fe4e090beb915950cdc9972e72e04959086` and created version commit
`fb2c6ff4bb5bbad936958e3651712b05b8c11a9a` with annotated tag `v0.44.4`.
The hook's full canonical run `c735be26bf924513ad8c6473b1fe8b72` passed 4,571 tests,
30 skipped, 81 deselected and 178 warnings in 1,058.53 seconds, plus all static/import
checks. An earlier hook attempt was interrupted after detecting a different CUDA
visibility environment; it is not a passing check. No hook was bypassed.

The subsequent queue configuration request is implemented separately in queue 0.1.6,
commit `2fbaed25fa7c572757d30cb9b1b343d22e645e3a`. Fresh independent review accepted
its implementation and portable guidance. CY's portable documentation now describes
the optional positive finite `queue.max_used_memory_gib`, default 2.0, strict-below
admission, a frozen guardian startup value and worker restart/upgrade requirements.
The existing queue roots, coordination ownership and direct estimator checks remain
unchanged. Only the operations tutorial's Markdown/HTML changes packaged content;
no additional CY runtime Python or tests changed. Its separate no-impact architecture
record passed both validation phases.

The final source environment was normally resolved and installed as CY 0.44.4 plus
queue 0.1.6, and all 286 packages passed `uv pip check`. The original source overrides
and operational environment remain untouched. The earlier proposed-pair checks are
retained as history; final checks below cover the actual source and metadata view.


The final queue pair passed 544 tests with seven physical-GPU cases deselected,
plus static/import, help, dependency and source/installed identity checks; see
[final pair evidence](paired.md). The queue documentation follow-up passed all
199 documentation/catalogue compatibility tests and the complete Markdown/link
verifier. Fresh reviewer `review_queue_memory` found two stale fixed-limit guides
and a private numeric preference in the no-impact record. The parent corrected
those, additionally reconciled runtime-isolation guidance, and expanded the record's
scope. The reviewer rechecked the final guides, generated operations HTML, whitespace
and no-impact acceptance and returned **ship** with no unresolved findings. No CY
Python or tests changed during this documentation follow-up.

Final canonical run `66a11f98161148a385e459119a55a23f` passed Ruff, strict mypy,
Vulture, all 52 import contracts and **4,571 tests**, with 30 skipped, 81 deselected
and 178 warnings, in 1,042.12 seconds. The verifier recorded its successful
application receipt. Fresh source inventory checks again matched all 560 selected
CY files and 73 queue files with zero differences. Final Markdown/link verification
passed before the documentation commit. Public ref verification remains pending
the authorized pushes; native benchmark gaps remain unchanged.

## Verified publication, 2026-10-30

The documentation follow-up committed through normal hooks as
`ffd294c3ac3240a282f87b76b7f40fa6dd963a44`, without another version bump. An atomic
push published CY master at that commit and annotated `v0.44.4`. Remote inspection
matched tag object `969f800b4a7de8541c75ff49fa4479214fb6adeb` and its peeled release
commit `fb2c6ff4bb5bbad936958e3651712b05b8c11a9a`. Queue main was pushed and remotely
verified at `2fbaed25fa7c572757d30cb9b1b343d22e645e3a` (source version 0.1.6).

The companion usage collection's annotated `v0.6.7` and main branch were also
atomically pushed and remotely verified; see [exact refs](portable.md#verified-publication).
T045 and T046 are complete. The final closure commit changes only this dated
evidence and the task ledger; it requires documentation checks and unchanged-input
hook verification, without a new version bump.

The original dirty workspace, its source overrides and pre-existing workloads were
preserved. No GitHub Release object, release asset, package publication or deployment
was created. T041 and full T044 native acceptance remain open under the explicit
delivery exception; successful CPU/process checks do not close those gaps.


## Completed matched native comparison — 2026-11-05

The explicit force amendment now provides the authorized execution path for the
SC-006 comparison on this host. The original idle-preflight failures above remain
historical failures. This run is **forced/background-sensitive**, not idle-device
evidence; strict ordinary admission remains unchanged. SC-006 requires actual
elapsed time, trial count and outcomes with matching workload/assets.

All six one-GPU searches completed through the production case-worker path using
320-pixel inputs, four classes, twenty objects per image, a batch ceiling of eight,
90% memory budget, 300-second trial deadlines, every native optimizer, five warmup
and ten measured steps plus validation. Every result is ceiling-limited batch eight,
with a fresh independent confirmation. Raw requests and rank receipts match the
profile, workload, strategy, token, optimizer, batch and step counts. Assets and
resolved profiles match across strategies for each model.

| Model | Strategy | Elapsed seconds | Trials | Confirmed batch |
| --- | --- | --- | --- | --- |
| yolo11n.pt | exponential_binary_v1 | 517.49 | 5 | 8 |
| fcos/resnet50_fpn | exponential_binary_v1 | 58.45 | 5 | 8 |
| yolo11n.pt | memory_guided_v1 | 265.60 | 4 | 8 |
| fcos/resnet50_fpn | memory_guided_v1 | 41.12 | 4 | 8 |
| yolo11n.pt | memory_guided_aligned_v1 | 88.66 | 2 | 8 |
| fcos/resnet50_fpn | memory_guided_aligned_v1 | 25.14 | 2 | 8 |

Each ordinary relaunch reused saved evidence without changing catalogue bytes or
creating new case directories. The first harness incorrectly required the CLI's
`cached` label, which can refer to another selected recommendation strategy. That
assertion failure, first script, logs and two completed timing rows are preserved.
The corrected harness additionally forbids worker-pool creation during cache replay;
all four remaining cases passed that stronger direct check. It changes no product
code. The original valid legacy timings are retained, not repeated or relabeled.

These are one observation per model/strategy in execution order, with native compile
caches and concurrent bounded CPU checks; host load and cache warmth were not
controlled. They are measured timings, not a statistical or isolated speedup claim.
Deterministic linear-memory trial savings remain covered by the ordinary tests.
The full 64-model capacity matrix and physical multi-GPU acceptance are separate.

Both benchmark ownership receipts verify native process exit and released GPU
claims. The resumed invocation exited zero. Retained `search-benchmark.json` has
SHA-256 `223102ffe7283c904be36b62a08b026a015a0f6d828ad4ec95b00d84dc42b66c`; native request/receipt files remain in the task-owned evidence
inventory. Runtime/profile bytes remained frozen. The final integrated canonical
run passed 4,790 tests, static/import checks and architecture negatives; the proposed
CY 0.46.0 / queue 0.1.9 pair passed 583 ordinary tests with seven physical cases
explicitly deselected. Documentation validation and final record review follow.


Fresh independent reviewer `hf_conversion_review` accepted SC-006 after inspecting
all seven retained native case results and 43 optimizer rank receipts. Six reported
rows uniquely match the final cases; current assets rehash correctly and candidate
runtime source bytes match integration. The initial guided YOLO case completed
five trials before the harness assertion failed; the resumed reported case used
four. Both remain retained. This variation further limits any performance inference;
it is not hidden by the corrected harness or the six-row report.

The reviewer accepted the explicit force-path comparison and conservative timing
claims, confirmed exact preservation of the first two legacy rows and ownership
cleanup, and found no blocking gap. See [review.md](review.md). This acceptance does
not cover the full model matrix or physical DDP.
