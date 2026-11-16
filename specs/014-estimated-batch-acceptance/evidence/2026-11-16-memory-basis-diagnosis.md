# Ticket 99: CUDA/NVML reserve accounting diagnosis

Date: 2026-11-16. This is diagnosis and regression guidance for
[FR-006 and SC-004](../spec.md), not implementation verification or final acceptance.
The original ticket 09 and queue admission attempts remain **failed**. No run is
retrospectively accepted, and no GPU work was performed during this investigation.

Investigation used `/mnt/wsl/data/nkt/clearml-yolo`, local `master` at
`137079d099490e2153405f042befe8325e9a38bc`, equal to local master. Remote references
were not fetched. Concurrent ticket 99 implementation is separately owned; this
record describes the original launch source, not its in-progress replacement.

## Preserved failure and timing

Launch directory:
`.tmp/verification-gap-closure/backend-preparation/ticket09-20261116T160633Z-c6bea1ab`.
Case directory:
`runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-json-4ac8ff2faa`.
The launcher began at `2026-11-16T16:06:33.248887Z` and finished at
`16:08:20.979613Z`, recording failed status, exit 1, and both outer and worker
cleanup complete. Its execution timer was 103.99834 seconds; the native case
summary records 100.07951 seconds. Pytest reports one failure in 102.39 seconds.
The different timers cover different scopes.

The batch store retains successful probes at 8 and 16, with no admitted capacity.
The third probe is identified by its retained request as **batch 24**, token
`1d5ae134213746ab825836699af82e46`, optimizer AdamW. The request was last written at
`16:07:57.226568Z`; its rank receipt at `16:08:18.331441Z` records allocator OOM.
It reports a 22 MiB attempted allocation, 15.71 GiB allocator allowance,
15.42 GiB allocated and 289.44 MiB reserved but unused, while CUDA reported
14.36 GiB free. These are the rounded values in the original exception.

The separate native harness reserve guard failed. The third OOM did not become a
completed search trial in the batch store before interruption. Consequently,
successful earlier probes and the rank OOM do not constitute a validated capacity
or authorize training. The original native log is empty; the traceback is retained
in the launcher pytest log.

## Demonstrated mixed-total false positive

The original `gpu_states()` queried NVML total and free, defining unavailable bytes
as `NVML total - NVML free`, including driver reservations. `GPUDevice.total_memory_bytes`
came from CUDA. `require_memory_reserve()` then subtracted those NVML unavailable
bytes from the different CUDA total.

| Quantity | Captured value |
| --- | ---: |
| CUDA total, guard traceback | 34,162,343,936 bytes = 32,579.75 MiB |
| NVML total, outer observations | 32,607 MiB |
| NVML free, minimum outer observation | 10,261 MiB |
| NVML total minus free | 22,346 MiB = 23,431,479,296 bytes |
| Guard unavailable bytes, traceback | 23,431,479,296 bytes |
| Guard reconstructed free | 10,730,864,640 bytes = 10,233.75 MiB |
| Selected reserve | 10,737,418,240 bytes = 10,240 MiB |

The raw NVML total/free pair reproduces the guard's unavailable-byte value exactly.
Subtracting it from CUDA total shifts inferred free downward by **27.25 MiB**.
It therefore reports a **6.25 MiB deficit** while the corresponding raw NVML free
value is **21 MiB above** the selected floor.

The outer log contains 99 samples, with its minimum at elapsed 101.82287 seconds;
the last two samples return to 26,991/26,990 MiB free. With the observed constant
NVML total, the failing guard's exact unavailable-byte value implies 10,261 MiB
NVML free. Independent queries need not be the same physical query to reproduce
this arithmetic. No shorter, unlogged raw-memory dip is required to explain the
failure. Earlier commentary suggesting such a dip was an inference and is corrected
by these retained values.

This demonstrates a reserve false positive from incompatible total bases. It does
not establish a raw NVML breach of 10 GiB, and it does not establish an 8 GiB user-floor
breach. Sampling cannot prove every intervening transient. The allocator OOM is a
separate observed outcome and remains valid evidence of that attempted allocation.

## What the allocator evidence does and does not establish

The original allocator guard used the smaller of CUDA free and
`CUDA total - NVML unavailable`, added the process's current reserved bytes, then
subtracted the requested reserve and 256 MiB growth headroom. It shares the same
total-basis error. The allowance constrains the PyTorch allocator; it does not cap
foreign processes or every native-library allocation.

This attempt did not retain an exact initial allocator-budget snapshot or enough
per-process memory history to distinguish native non-allocator growth, external
usage changes, or every source of headroom consumption. Successful probes retained
their CUDA non-allocator envelopes, but those values do not identify the failed
trial's live whole-device consumers. Calling this failure external resource
instability or proving the 256 MiB allowance insufficient would overstate the record.
Correct the demonstrated arithmetic before drawing those conclusions.

The public `SearchSettings.memory_fraction` limits search prediction and acceptance
of measured peaks; it is not an independent per-process allocator cap. The same
`minimum_free_memory_bytes` currently reaches allocator setup and reserve monitoring.
Existing settings therefore cannot independently select a 10 GiB allocator target
and an 8 GiB monitor floor. Raising their shared value moves both thresholds and
does not create additional separation. No new split-floor policy is approved here.

## Minimal correction and regression boundaries

The bounded candidate preserves CUDA device totals/profile identity, retains raw
NVML unavailable bytes, and carries NVML free bytes explicitly. Inventory/admission/
monitor outputs can use `max(CUDA total - NVML free, 0)` when their consumer expects
CUDA-capacity-relative unavailable bytes. Allocator budgeting should use
`min(CUDA free, NVML free)` directly. Direct harness and campaign observer consumers
must also stop subtracting raw NVML unavailable bytes from CUDA total.

Clamping is deliberately conservative: reconstructing free from normalized used
produces `min(CUDA total, NVML free)`. It exactly preserves the physical-free reserve
decision for feasible floors at or below CUDA capacity, including this campaign's
8/10 GiB floors. It does not imply exact equality when NVML free exceeds CUDA capacity
and a requested floor itself exceeds that capacity. Test and describe that saturation;
do not introduce negative inventory-used values or change profile totals to hide it.

Recommended CPU product regressions cover the recorded tuple, equality and one-byte
failure boundaries; both total-disagreement directions; nonnegative saturation;
raw driver-reserved accounting; reversed device/response order and UUID mapping;
missing/invalid telemetry; foreign-process rejection; allocator free-source selection,
current-reservation accounting, existing growth headroom, zero no-discovery behavior;
and the direct native harness reserve check. No tooling-only tests are requested.

The cy-queue product owns separate GPU telemetry and does not import these CY
inventory APIs. Ticket 92's campaign instrumentation does import `gpu_states()` and
is an affected direct consumer. The correction must not change queue coordination,
occupancy configuration, CUDA profile identity or dependency pins.

## Earlier queue failure and remaining gates

`runs/verification-gap-closure/assets-v1/queue-acceptance-v1/completed/admission/`
retains a failed batch-72 admission attempt. The store shows successful probes,
an OOM at 72, success at 64, then contaminated confirmation at 64 because the
8 GiB reserve check failed. Its retained confirmation record does not include a
sufficient total/free/used tuple to prove this same false positive. The shared code
defect makes that explanation possible, not demonstrated. Controller cleanup passed;
no queued job was submitted. This attempt remains failed.

Implementation, affected CPU/static/mutation verification, fresh independent review
and subsequent native revalidation remain separate work. No new acceptance, waiver,
GPU retry, commit or release follows from this diagnosis.

## Hashes of retained evidence

Paths below are relative to the launch/case directories identified above.

| Evidence | SHA-256 |
| --- | --- |
| Launch `result.json` | `2cea70f5dd3cf8695d62f1b7f8c5168901ce8fcdfdfe68babba62e0199ed3677` |
| Launch `gpu-telemetry.jsonl` | `d8ad2f61dc5d0407b4055966819457a9e7e66349ca284523b2ad2b22beabcb8f` |
| Launch `pytest.log` | `756ec07c525e42f5bc2ad0aaa61c6919063f5381bfbd51102cfc5d53b353d1ed` |
| Case `summary.json` | `1d291fb9eb3fb8e3bebd7a03c5afad0f95e710ee744135beaa625132d462bf0d` |
| Case `batch-estimates.json` | `bb226f1a4becbb65250b10f9ff3ba30a8c9ddcd494f9566b0f6837f7315cf1b8` |
| Third probe `request.json` | `bb5b14bd9009f755ca8103076947848371efe00e4547802eabcf9272d83e1ea9` |
| Third probe `rank-0.json` | `e36d8aa914690be416b9b79310673851154246d48de96fc2e2a5fa872164ae39` |

The third probe files are under
`.tmp/batch-estimate/1d5ae134213746ab825836699af82e46/AdamW/` in the case directory.
Original launch source hashes: `gpu_inventory.py`
`b97a7b58b2fd2951a3a77b4a142d8e8554fafa8581b1486c4c07dab8f3900384`;
`gpu_memory.py` `abb71bc16eb552c2176c73a9a592d6c7091f9839abb8c166da426b33ab3b0502`;
`tests/severstal_batch.py` `98615fbb5a07f3e372530e27fdf18e4117fdbfbc5c5a221f14d6804f5e900f6f`;
`tests/severstal_harness.py` `cf57290490e54e1997096ad22afbbe3c9668c290b393cf62238da34397698c7f`.

Queue evidence hashes: `admission/receipt.json`
`d3cb68a40375c6328b3ba6d0ef589528ef4bd04008589c32c39a5eb9611ad38f`;
`admission/batch-estimates.json`
`12e23f8f6407274d11ee13bdf650beafa6c9e4af341aca2d8656a04f7430879c`;
`controller-result.json` `c5c4cd8e90ca9b3e022f83e7e59f70b365b7d3d2fc63cca08695cefac1b9b321`.
