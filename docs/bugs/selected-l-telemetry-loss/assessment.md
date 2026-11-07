# Selected-L GPU telemetry loss assessment

- Date: 2026-11-07.
- Slug: `selected-l-telemetry-loss`.
- Source: remaining-work plan [WP1 T1.1](../../plans/remaining-work-20261106/plan.md#wp1-native-forced-estimator-acceptance-single-gpu).
  It covers the telemetry failures recorded in
  [accelerator-oom test.md](../accelerator-oom-receipts/test.md) and
  [DINOv3 test.md](../dinov3-hf-native/test.md#selected-l-diagnostic-outcomes--2026-11-06):
  "helper ENOMEM", helper exit 255 and a 15-second `nvidia-smi` query timeout.
- Verdict: **environmental, reproduced (3 of 3).** The DEIMv2 L batch-8 trial needs
  far more than the 32 GiB device memory. On this WSL2 host, CUDA does not raise a
  native OOM; WDDM silently oversubscribes into Windows shared system memory. Windows
  adapter Shared Usage grew to about 92 GB, and Total Committed reached about
  134 GB on a 127.4 GB host. The paravirtualized GPU driver path then became
  unavailable for about 11–12 seconds, and NVML, `nvidia-smi` and its executable
  lookup failed or blocked. It is not a CY telemetry defect. Three secondary CY
  diagnosability defects are confirmed (below); they did not cause the failure.
- Status (2026-11-07): the user chose option 1, the driver setting. A guarded probe
  showed that WSL2 CUDA does not honour it in the current WSL VM and driver session
  ([test.md](test.md#sysmem-fallback-policy-check--2026-11-07)):
  - 33 GiB was allocated on the 31.8 GiB device with no OOM;
  - Shared Usage grew by 3.6 GB.

  WP1 stays blocked. Option 2 is now needed to unblock it; option 3, an accepted
  gap, remains the alternative.
- Status (2026-11-07, post-restart): **not verified.** The WSL VM restarted (boot
  15:08:47 MSK), but the probe was not rerun, because the user was watching video
  and the probe needs more VRAM than pcboard's safe headroom
  ([test.md](test.md#post-restart-sysmem-fallback-probe--2026-11-07)). Whether a
  restart makes the setting take effect is still unknown. Option 2 (an
  allocator-enforced budget) or option 3 (recorded gaps) remains.

## Observation

The forced selected-L estimate (`deimv2/l`, 960 px, 150 classes / 300 objects,
one RTX 5090, budget 0.9, limit 1024, 300 s trials, `--force`) failed in all three
fresh runs on CY 0.46.1, 2.5–4 minutes into the first batch-8 trial
([test.md](test.md)). Observations:

- In every run, `nvidia-smi` device memory reached about 32.0 of 32.6 GiB. That is
  above the 0.9 budget even after subtracting the about 1.5 GiB background baseline.
- In every run, a side-probe query blocked for 9.5–11 seconds, just under the
  15-second deadline. Run 1 kept only the catalogue diagnostic, so its leaf failure
  is not recorded.
- In runs 2 and 3, the guest dxg driver's normally continuous `dxgkio_escape`
  kernel messages stopped completely for about 11–12 seconds. Inside that window:
  - `nvidia-smi` exited 255 within 6–8 ms ("couldn't communicate with the NVIDIA
    driver", "Failed to initialize NVML: Generic operating system error");
  - the estimator's own `--query-compute-apps` call exited 12 (run 2);
  - the executable lookup failed (run 3).
- After the parent's telemetry failure, the worker did not exit within the
  2-second bounded wait, and the native scope reported surviving owned descendants.
  That is consistent with a process blocked in the driver. The owned outer guard then
  verified descendant exit and released the reservation.

The third, sampled run identified the mechanism.

- Within about 10 seconds of the CUDA context appearing, Windows adapter Dedicated Usage
  saturated at about 32.1 GB.
- Shared Usage then rose in steps: about 31 GB by 06:15:44, 60 GB by 06:17:28,
  82 GB by 06:18:19 and 91.8 GB at 06:18:57.
- Total Committed reached 133.6 GB, and the host has 127.4 GB physical RAM.
- The worker thread was repeatedly in uninterruptible sleep in
  `dxgvmb_send_sync_msg`, a synchronous VMBus request to the host GPU kernel.
- The driver silence (06:18:52–06:19:02) began at the shared-memory peak.
- Inside it, the parent's `shutil.which("nvidia-smi")` found no executable
  (`RuntimeError: Batch estimation requires nvidia-smi GPU telemetry`), so the WSL
  GPU library path itself was transiently inaccessible.

The three original symptoms (ENOMEM label, 255, timeout) are therefore
manifestations of one event: the host-side GPU path became unavailable under
Windows memory exhaustion caused by device-memory oversubscription. Its lookup,
initialization and query failures surface as different errors. Host-side memory
exhaustion in that path is a plausible origin for an `ENOMEM` (or "Generic
operating system error") seen inside the guest. This is an inference; Windows-side
free memory was not sampled at the instant of failure. The original raw receipts
from 2026-11-06 could not be located on this host, so the mapping is shown on fresh
evidence rather than on the original files.

## Excluded hypotheses

- **Fork/commit ENOMEM from a large parent.** `vm.overcommit_memory=1`, and the
  telemetry caller is the estimator parent, not the CUDA worker. The parent RSS was
  small.
- **Host memory fragmentation or cgroup limits.** During the failure window, free
  order-4 blocks stayed around 18,000. `compact_stall`/`compact_fail` did not change.
  `MemAvailable` stayed around 57 GiB, and the unit peak was 2.9–3.9 GiB against
  `MemoryMax=48G`.
- **9p order-4 allocation failures.** These are real on this host. `nvidia-smi`
  loads `libnvidia-ml.so.1` and `libcuda.so.1.1` from the v9fs
  `/usr/lib/wsl/drivers` mount (`msize=65536`), and the kernel journal shows
  `p9_tag_alloc` order-4 `GFP_NOFS` failures on 2026-11-06 09:21/09:29 and
  2026-11-07 00:30/00:32. None occurred during either reproduction. They explain the
  owner's separate 2026-11-07 filecmp `OSError: [Errno 12]`: the 00:32 kernel trace
  is a `python3` `read()` through `v9fs_file_read_iter`, so the failing side of that
  comparison was on a 9p (drvfs) path, not on ext4 `/mnt/wsl/data`. That lead is
  unrelated to the telemetry failure.
- **A Windows TDR.** The Windows System log contains no nvlddmkm, Display or dxgkrnl
  event in the window.

The "ENOMEM" label in the earlier records is plausibly a misreading of
`CalledProcessError ... returned non-zero exit status 12`. Status 12 equals
`NVML_ERROR_LIBRARY_NOT_FOUND` in the installed `nvidia-ml-py` constants, which is
not errno `ENOMEM`. This cannot be verified without the original receipts.

## Code paths

- `adapters/runtime/gpu_inventory.py` `_query`: `subprocess.run(..., check=True,
  timeout=15)` per query. Two queries run per `gpu_states()`, through
  `monitor_devices` from the `batch_probe` monitor. Failing on missing telemetry is
  the documented contract ([batch estimation](../../batch-estimation.md): "Missing or
  unidentifiable telemetry fails the affected measurement"). A retry, a longer
  deadline or a fallback would change that contract, not fix a defect.
- `adapters/runtime/workers.py` `run_workers`: the monitor exception plus the
  bounded-cleanup `TimeoutExpired` become `BaseExceptionGroup("Worker execution and
  cleanup failed")`. This is correct fail-closed behavior.

## Secondary diagnosability defects (confirmed, not root cause)

1. `application/use_cases/batch_estimate.py` records `f"{type(error).__name__}:
   {error}"`. For an exception group, that keeps only `"... (2 sub-exceptions)"` and
   drops every leaf: the `CalledProcessError`, the cleanup `TimeoutExpired` and the
   surviving-descendant `RuntimeError`.
2. The exception group escapes `NativeBatchProbe.run`'s `except RuntimeError`, so the
   failed batch-8 attempt is not recorded as a trial (`trials: []`).
3. `CalledProcessError` text omits `nvidia-smi` stdout, where NVML prints its error.

Remediation proposal (follow-up bug, not delivered here): format exception-group
leaves recursively in the case diagnostic, and attach the query's stdout/stderr
through `add_note` without changing exception types. Keep the existing type-based
status mapping. Wrapping in a `RuntimeError` whose text contains "GPU" would
reclassify these failures as `contaminated` through
`"contaminated" if "GPU" in str(error)`. Regressions would construct the nested
group and a failing query, CPU-only. This would improve evidence; it would not make
the selected-L measurement succeed.

## Impact on WP1

WP1 is **blocked, not postponed**. No pcboard busy or stop signal occurred.

- The estimator rejecting lost telemetry is correct by contract. No deadline,
  workload, budget or search setting may change.
- Batch 8 clearly exceeds the 0.9 budget: device plus shared usage was about
  124 GB, against a 28.6 GiB budget. On native Linux CUDA this would be a native
  OOM and, after cleanup, the contract's minimum-eight `no_capacity`. Here no
  completed receipt proves it, so none is claimed.
- Each such trial drives the Windows host towards physical memory exhaustion. That
  also threatens the user's desktop and unrelated workloads. Repeating it is not a
  harmless retry.
- DEIMv2 X and any other catalogue model whose minimum batch exceeds device memory
  are exposed to the same failure; T1.2–T1.4 inherit this risk.

Unblocking needs a user decision. None of these options was applied here:

1. **Host driver setting.** Set the NVIDIA "CUDA - Sysmem Fallback Policy" to
   "Prefer No Sysmem Fallback" (globally or for the WSL host process), then replay
   this scenario. *(2026-11-07: chosen and applied globally by the user. Without a
   VM restart or driver reload, WSL2 CUDA does not honour it: a 1 GiB allocation
   probe exceeded device memory with no OOM. The replay was not run. See
   [test.md](test.md#sysmem-fallback-policy-check--2026-11-07). After the WSL VM
   restart the probe has not been rerun yet, so the post-restart result is not
   verified; see
   [test.md](test.md#post-restart-sysmem-fallback-probe--2026-11-07).)*
2. **Source change (new contract decision).** Enforce the existing memory budget in
   the probe worker allocator, for example
   `torch.cuda.set_per_process_memory_fraction(memory_fraction)`. An over-budget
   trial then raises a native typed OOM, which the existing receipt path classifies,
   instead of oversubscribing. This changes how capacity is measured near the
   budget, because allocator fragmentation counts against the cap. It is therefore
   an estimator contract change for the user to approve, not a bug fix.
3. Accept selected-L (and affected models) as recorded gaps.

Global machine changes (driver settings, sysctls, `.wslconfig`) require explicit
user authorization.
