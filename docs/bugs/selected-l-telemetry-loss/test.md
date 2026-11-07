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
