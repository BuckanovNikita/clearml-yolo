# Selected-L GPU telemetry loss verification

Date: 2026-11-07. Result: original failure class reproduced natively (3 of 3);
classified environmental. No source change; no release.

## Setup

- Source: CY 0.46.1 (`origin/master` `ce7e48e`) in a task worktree with frozen
  `uv sync`. A fresh task-owned `CY_HOME` downloaded the DEIMv2 source; the DINOv3
  backbone came from the existing Hugging Face cache.
- GPU admission: the existing owned launcher acquired the cy-queue local GPU lease
  with the 12 GiB used-VRAM admission rule. It ran a transient user unit with
  `MemoryMax=48G` and `KillMode=control-group`. At admission the background usage
  was 1,540 MiB, 0 % utilization, with no compute PIDs. No pcboard busy line appeared
  at any point.
- Identity: local run identity `t11-telemetry-20261107-dc140632`. `infra.py room`
  returned WAIT on the unrelated FAT namespace slot, so no stand tag was minted.
  `cy-batch-estimate` creates no ClearML task, so no ClearML objects exist for this run.
- Observer (outside CY):
  - a `dmesg -w` capture;
  - 1 Hz `/proc/buddyinfo`, `/proc/vmstat` compaction/allocstall and `/proc/meminfo`;
  - a side probe running the two exact production `nvidia-smi` queries every second
    with the 15-second deadline.

## Runs

| Run | Command | Result |
| --- | --- | --- |
| 1 | `cy-batch-estimate --imgsz 960 --classes 150 --objects-per-image 300 --models deimv2/l --devices 0 --memory-budget 0.9 --search-limit 1024 --trial-timeout 300 --force` | Exit 1 after 169 s. Case `failed`: `ExceptionGroup: Worker execution and cleanup failed (2 sub-exceptions)`, `trials: []`. Unit peak 3.9 GiB. Exit verified, lease released. |
| 2 | Same `estimate_batches` path through a diagnostic driver that subclasses `NativeBatchProbe.run` only to print the full exception tree | Batch-8 trial 06:06:45–06:10:12 raised the same group. Leaves: `CalledProcessError` (`nvidia-smi --query-compute-apps=gpu_uuid,pid` exit **12**); nested cleanup `TimeoutExpired` (worker `wait(timeout=2)`); `RuntimeError: Owned descendants survived bounded cleanup`. Unit peak 2.9 GiB. Exit verified, lease released. |

| 3 | Run-2 driver, plus Windows `GPU Adapter/Process Memory` counters (read-only `Get-Counter`, about 1.6–1.8 s spacing) and 2 Hz worker thread state/`wchan` | Batch-8 trial 06:15:12–06:19:08 raised the same group. Leaves: `RuntimeError: Batch estimation requires nvidia-smi GPU telemetry` (`shutil.which` found no `nvidia-smi`), cleanup `TimeoutExpired`, surviving-descendant `RuntimeError`. Unit peak 2.9 GiB. Exit verified, lease released. |

## Timeline evidence (MSK)

Run 1:

- device memory held 32,020–32,064 MiB during the trial;
- one side-probe inventory query at 06:04:47 took 9.52 s with exit 0;
- device memory then fell to 257 MiB at 06:04:57 after teardown.

Run 2:

| Time | Observation |
| --- | --- |
| 06:09:30–06:09:56 | Device memory 31,999–32,016 MiB, 0–100 % utilization. `dxgkio_escape` messages are continuous (3–30 per second). |
| 06:09:53–06:10:05 | No dxg kernel messages at all. |
| 06:09:57.688 | Side probe exit 255 in 0.008 s: "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver … Failed to properly shut down NVML: Driver Not Loaded". |
| 06:09:59.984, 06:10:01.152 | Side probe exit 255 in 0.006–0.007 s: "Failed to initialize NVML: Generic operating system error". |
| 06:10:01.160 | Side-probe compute-apps query blocked 10.965 s, exit 0. |
| ≈06:10:0x | Estimator query exits 12, worker teardown and cleanup timeouts follow. |
| 06:10:13 | Device memory 257 MiB; queries return to about 0.1 s. |

Host memory in the run-2 window:

- `MemFree` was about 18.6–20.3 GiB and `MemAvailable` about 58 GiB;
- free order-4/5/6 Normal-zone blocks stayed at about 18,045 / 11,491 / 2,979;
- `compact_stall` stayed 212,125 and `compact_fail` stayed 137,336;
- no `page allocation failure` was logged.

Run 3 Windows adapter memory (GB, `GPU Adapter Memory` counters):

| Time | Dedicated | Shared | Note |
| --- | --- | --- | --- |
| 06:15:27 | 0.3 | 0.2 | Before the CUDA context. |
| 06:15:39 | 32.0 | 5.0 | Dedicated first rose at 06:15:29 and saturated about 10 s after the CUDA context appeared. |
| 06:15:44 | 32.1 | 31.3 | |
| 06:17:28 | 32.2 | 59.9 | |
| 06:18:19 | 32.2 | 82.5 | |
| 06:18:57 | 32.1 | 91.8 | Total Committed 133.6; the host has 127.4 GB RAM. |
| 06:18:52–06:19:02 | — | — | No dxg kernel messages; side-probe query blocked 10.5 s. |
| 06:18:59–06:19:11 | 0.6 → 0.3 | 91.3 → 0 | Teardown. |

During the trial, the worker thread was repeatedly sampled in D state with
`wchan=dxgvmb_send_sync_msg`. Linux guest memory again showed no fragmentation,
compaction or allocation-failure events.

## Host checks

- `vm.overcommit_memory=1`, `max_map_count=262144`, `compaction_proactiveness=0`.
  The `ulimit -a` memory limits are unlimited, apart from 64 MiB locked memory.
- `nvidia-smi` dlopens `/usr/lib/wsl/drivers/nv_dispi.inf_amd64_*/libnvidia-ml.so.1`
  and `libcuda.so.1.1` (`LD_DEBUG=files`). That directory is v9fs with `msize=65536`.
- Kernel journal for the current boot:
  - 9p `p9_tag_alloc` order-4 `GFP_NOFS` failures at 2026-11-06 09:21 and 09:29
    (`rg`, readdir), and at 2026-11-07 00:30 (`grep`) and 00:32 (`python3`, `read()`
    through `v9fs_file_read_iter`);
  - `vmbus_alloc_ring` order-7 failures at 2026-11-05 21:11, 2026-11-06 14:09 and
    2026-11-07 00:45;
  - none during either reproduction.
- The Windows System log over the previous 30 hours has no nvlddmkm, Display,
  dxgkrnl, WHEA or resource-exhaustion events.
- Idle warm queries take 0.07 s. A `POSIX_FADV_DONTNEED` eviction attempt left the
  driver libraries fully resident, so cold-load timing was not measured.

## Limits

- The original 2026-11-06 raw receipts were not found, so the earlier "ENOMEM"
  label cannot be checked directly.
- Device-memory oversubscription into Windows shared memory is measured. The exact
  Windows-internal failure in the driver path (for example host memory exhaustion
  versus paging latency) is inferred, not observed: Windows free memory was not
  sampled at the failure instant, and Windows kept no driver event.
- No production telemetry fallback, retry, timeout relaxation, workload reduction or
  machine setting change was made.
- Raw observer, launcher and run logs are retained in the task-owned run directory.

## Sysmem fallback policy check — 2026-11-07

Result: **not honoured.** CUDA in WSL2 still oversubscribes into Windows shared
memory with the driver setting applied. Step 2 (the selected-L replay) was not run.

### Decision and setting

- The user chose option 1 from the [assessment](assessment.md#impact-on-wp1). In
  NVIDIA Control Panel → Manage 3D settings → Global, they set "CUDA - Sysmem
  Fallback Policy" to "Prefer No Sysmem Fallback" on the Windows host.
- No WSL VM restart, driver reload or reboot followed the change. Other agents were
  running, so none was forced.

### Safety guard

- A task-owned watchdog wrapped the probe:
  - a persistent `powershell.exe` `Get-Counter -Continuous -SampleInterval 1`
    sampler, at about 1.0 s spacing;
  - an abort on NVIDIA adapter Shared Usage more than 4 GB above the pre-launch
    baseline;
  - an abort on adapter Total Committed above 110 GB;
  - an abort on samples stale for 5 s.
- Deviation from the requested guard: the 110 GB limit applies to the adapter
  `GPU Adapter Memory(luid_…120b6_phys_0)\Total Committed` counter. The 133.6 GB
  figure in run 3 came from that counter. System `\Memory\Committed Bytes` is
  about 140 GB at idle on this host, because it is backed by the page file, so a
  110 GB limit on it would trip at once. It was recorded only.
- Abort action:
  - SIGKILL the owned launcher's transient unit through `cgroup.kill`, then
    `systemctl --user kill`;
  - let the launcher verify exit and release its lease, then SIGKILL the guarded
    process group if it survives;
  - verify through `/proc`, the unit cgroup and a bounded `nvidia-smi` query.
- Kill-path tests passed before any GPU step:
  - a direct `sleep` tree: three PIDs killed, none left;
  - the owned launcher running `sleep 300` in a `MemoryMax=48G` unit: unit killed
    after 15 s, `process_exit_verified` and `ownership_released` true.

### Probe

- Path: the same owned launcher, cy-queue lease and 12 GiB admission rule as T1.1.
  pcboard was `normal`; background usage was about 2.0 GiB.
- Command: `uv run --frozen --no-sync python probe.py` in the primary checkout.
  CY master `49b2125`, torch 2.14.1+cu130.
- Method: allocate and fill 1 GiB `torch.uint8` CUDA blocks with a synchronize after
  each. Pace at 1 s per block from 24 GiB. Self-stop at 33 GiB, because exceeding the
  31.8 GiB device without an error already decides the result.
- Outcome: 33 GiB allocated, **no exception** (`hard_stop_no_exception`).
  - `torch.cuda.mem_get_info` reported 0 GiB free from 29 GiB onwards.
  - Allocations kept succeeding, slowing from about 1.0 to 2.3–3.2 s per GiB.

Windows NVIDIA adapter counters (GB, 1 s; MSK):

| Time | Dedicated | Shared | Adapter Total Committed | System Committed |
| --- | --- | --- | --- | --- |
| 11:29:23 | 2.0 | 0.1 | 3.7 | 139.9 |
| 11:29:29 | 31.0 | 0.2 | 33.4 | 169.6 |
| 11:29:33 | 31.1 | 1.8 | 35.4 | 171.8 |
| 11:29:37–38 | 31.1 | 3.8 | 37.5 (peak) | 173.7 (peak) |
| 11:29:41 | 0.8 | 0.4 | 3.8 | 140.3 |

- The Shared Usage peak was baseline + 3.6 GB. That is just under the 4 GB abort
  limit, so the watchdog did not trip.
- Exit was clean, with `ownership_released` true, no owned PIDs and an empty unit
  cgroup. Device memory then read 770 MiB.

### Verdict and impact

- Verdict: not honoured. The "native OOM" criterion failed. Shared Usage grew
  +3.6 GB against the +1 GB criterion, which also failed.
- The selected-L replay would again drive Windows into the run-3 exhaustion path,
  so it was not run.
- Option 2 is required: an allocator-enforced budget, a source and contract change.
- Untested caveat: the setting might take effect only after a full WSL VM restart
  or a driver reload.

### Receipts

The raw files are kept outside the repository in the task-owned
`nofallback-20261107` evidence directory:

- watchdog `summary.json` and `samples.tsv`;
- launcher `ownership.json` and `run.log`;
- the probe, sampler and watchdog scripts.

## Post-restart sysmem fallback probe — 2026-11-07

Result: **not verified.** The probe was not run after the restart, so it is still
unknown whether WSL2 CUDA honours "Prefer No Sysmem Fallback" once the WSL VM has
restarted. The latest measured result is still the
[pre-restart check](#sysmem-fallback-policy-check--2026-11-07): not honoured.

### Why the probe did not run

- The current WSL VM booted at 2026-11-07 15:08:47 MSK (`uptime -s`).
- At 15:16 pcboard reported that the user had been watching video (`chrome.exe`)
  since 15:00. VRAM was 3.4 of 31.8 GiB, and only small GPU jobs were allowed,
  with about 27 GiB of safe headroom.
- The probe fills 31–33 GiB of device memory, so it is not a small GPU job. Under the
  pcboard GPU safety rule it was not started.
- `pc_status(wait=free)` was registered at 15:16:03 under the parent session key.
  It had not fired when the step returned, so no wait duration is recorded.
- No launch root was created, no probe ran, and driver versions were not captured.

### Independent check

- The receipt directory holds only `wait-start.txt`, `pcboard-blocked.log` and
  `SHA256SUMS`. `sha256sum -c`, run inside the directory, reports both files OK.
- There is no `summary.json` or `samples.tsv`. With no exception type and no
  Shared/Committed trace from a post-restart run, "honoured" cannot be claimed.
- The block is justified: the probe needs more device memory than the safe headroom
  pcboard reported.

### Rerun procedure

Rerun once `pc_status(wait=free)` fires, with the same procedure as the pre-restart
probe:

- `watchdog.py` wraps the owned launcher `run_owned_gpu.py`, which runs
  `uv run --frozen --no-sync python …/scripts/probe.py` in the primary checkout with
  `--seconds 300`.
- Keep the same abort thresholds: Shared Usage 4 GB above the baseline, adapter Total
  Committed 110 GB, samples stale for 5 s.
- Write the receipts into `step1-probe-postreboot2/` under a new launch root.
  Capture the Windows and WSL driver versions next to the probe, and update
  `SHA256SUMS`.

### Impact

WP1 stays blocked. Option 2 (an allocator-enforced budget) or option 3 (recorded
gaps) remains the way forward. Option 1 would only become viable again if a measured
post-restart probe showed a native OOM with no Shared Usage growth.

### Post-restart receipts

The files are in the `nofallback-20261107/step1-probe-postreboot2/` evidence
directory, outside the repository.
