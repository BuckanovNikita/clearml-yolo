# Ticket15 telemetry interruption — 2026-11-16

Status: two full attempts failed; idle health and one isolated native probe passed.
The historical stall's underlying cause remains unproven. No product or monitor
change was made, and this record does not accept ticket 15 or mark defect 101 fixed.
The [paired JSON](2026-11-16-ticket101-telemetry-timeout.json) binds both failed
launches and retained failure/diagnosis files, including the subsequent isolated probe. The
[estimated-batch acceptance contract](../../014-estimated-batch-acceptance/contracts/acceptance.md)
still requires valid current capacity confirmation before training.

The retained launch is
`.tmp/verification-gap-closure/backend-preparation/ticket15-20261116T174736Z-7fa92eb6/`;
case `deimv2-l-json-283120b759` is under the shared estimated-acceptance-v2 root.
Actual source was ba56e2f. At 17:49:49 UTC the launcher returned failed after its
exact `nvidia-smi --query-gpu=uuid,memory.total,memory.used,memory.free,utilization.gpu
--format=csv,noheader,nounits` subprocess exceeded the unchanged five-second limit.
The result receipt SHA256 is
`07d58464354bcf850efe6ff8bbf5210b44c9a78d32389743bbd556605f20a84f`.

The case retains batch 8 success, batch 16 allocator OOM and interrupted independent
batch 8 confirmation. A confirmation child result exists, but it does not validate
the cancelled enclosing invocation. No training, summary or accepted handoff was
produced. The 106 retained outer samples reached minimum free memory 10,370 MiB;
the final sample was 17,364 MiB. Missing telemetry is not a reserve pass. The
launcher reported cleanup complete, and subsequent inspection found its PID 885163
absent and no case/harness process matches. A fresh compute-app query exited 0
with no GPU process rows.

The bounded read-only probe in
`.tmp/verification-gap-closure/ticket101-telemetry-diagnosis/` repeated the exact
failed query 30 times: all passed, maximum latency 0.114 seconds. Its retained
probe.json SHA256 is
`751d94f16392ead3eb196fb318c35903fa15e01bd3e91d480e3de6f517cedff1`.
The separately retained kernel-window.log uses explicit UTC bounds 17:47–17:51.
It includes repeated dxg ioctl errors and completion-wait failures around
17:49:48–49. Their temporal correlation does not establish whether they caused
the stall or resulted from process interruption. No driver reset was performed.

Current responsiveness argues against a persistent telemetry outage. Transient
WSL/driver delay and host resource contention remain possible explanations;
neither was isolated. Export setup finished 17:48:38, before this failure, so its
completion is not evidence of a recovery or mitigation. Current memory availability
and process cleanup do not prove historical playback continuity or rule out a
past stall.

Independent reviewer final_recipe_review verified the failed receipt,30-query
probe, sample minimum and incomplete native outcome. The reviewer approved a
fresh bounded attempt after the current compute-PID check, retaining the exact
five-second telemetry deadline, 10 GiB operational reserve, two-epoch recipe and
fresh capacity estimation. That is current admission evidence, not a historical
root-cause claim. Preserve the original failure; another timeout must remain a
failure rather than trigger an automatic retry or relaxed guard.

## Fresh attempt and current disposition

The independently admitted fresh attempt
`ticket15-20261116T175546Z-ae01d6d8` also failed on the same exact five-second
nvidia-smi timeout, after 46.40 seconds. Its launcher reported owned cleanup
complete. This second observed failure during estimation means the idle health
probe did not establish reliability under workload. Full GPU matrix launches remain paused while the repeated failure is investigated;
a separately reviewed isolated diagnostic is recorded below. Both original attempts remain
failed; no timeout or reserve limit was relaxed. CPU-only evidence, environment
and queue-test work may continue independently.

## Bounded idle concurrency comparison

Independent source inspection identified three steady telemetry owners during
estimation: the outer launcher, harness worker monitor and native batch-probe
monitor. The outer owner runs one query per cycle with a five-second deadline;
each native owner runs GPU and compute-process queries sequentially, with the
existing fifteen-second per-query deadline. This permits three simultaneous
subprocesses, not five; rank allocator admission adds another transient owner.

The second failure occurred during the first batch-8 trial, before any OOM.
Therefore a preceding OOM is not necessary for the timeout. Successful ticket14
also had a 3.092-second outer sampling gap during training and common dxg `-22`
messages; those messages are not specific to failure. Completion-wait and `-512`
errors coincide with interruption and cannot independently prove its cause.

A separate read-only comparison ran twenty seconds serially and twenty seconds
with three owners: all 120 queries passed. Maximum durations were 0.103 and
0.111 seconds, with three overlapping query lifetimes actually observed. All
48 compute-process queries were empty; no CUDA context, model or allocation was
created. Every owned query process and supervisor exited. The successful window
still contained 360 dxg `-22` messages, with no completion-wait or `-512` errors.
The bounded round budget did not reproduce the native 0.25-second cadence, and
this negative idle result does not clear behavior under load.

Retained `idle-comparison/` evidence under the ticket101 diagnosis directory:
summary SHA256 `49ac54adde85182789b1e76d92ca9dbdfac8f2cf7d909c17d3088710ec0822c2`;
raw receipt SHA256 `c2e949f44946264a1e00ab3fcf705bcf2be7cb14cdfa43ada84c57690b901ebb`.
The subsequently reviewed and executed single batch-8 diagnostic is recorded below.


## Isolated native probe and bridge-wait observation

After root and independent review, one original DEIMv2 L batch-8 probe ran at
18:19:23 UTC on source `a71737e`, with the original request unchanged except its
unique token/output. All three guard owners, five/fifteen/fifteen-second query
deadlines, ten-GiB operational reserve and native trial timeout remained unchanged.
The scope was one capacity probe, without batch search, deliberate OOM, training
pipeline, publication or checkpoint acceptance.

The isolated probe passed: 5 warmup, 10 measured and 1 validation step; native
execution 32.904 seconds, enclosing execution 37.807 seconds. The 32 outer samples
had minimum free memory 17,252 MiB and maximum sampling gap 3.855 seconds. Cleanup
passed, observer joined, no observed survivors, received cancellation signals or
observer errors. These samples do not prove continuous reserve or video continuity.
Ticket15 and defect101 remain unresolved.

Process observations captured six slow queries in two overlapping groups, covering
all three guard owners and both GPU/compute-process query selectors. Each was
sampled in `D`/disk-sleep with `wchan=dxgvmb_send_sync_msg`, before the successful
rank receipt and without cancellation. This establishes a WSL GPU-bridge wait in
this successful run; it does not prove that concurrent monitors caused the wait,
or that the earlier uninstrumented failures had the same cause. The rank log was
buffered until receipt publication, so the triggering CUDA phase is unknown.

The original observer's epoch-minus-psutil-birth ages were biased by approximately
0.819 seconds because installed psutil adds integer `/proc/stat` boot time to
process start ticks. Retained `/proc/PID/stat` field22 and `CLOCK_BOOTTIME` correct
that comparison: the maximum sampled process age in the wait state was 3.213 seconds,
not the raw 4.032 seconds. Process age is not continuous wait duration; the longest
query was last observed alive at age3.525 seconds and first absent at3.628 seconds.
Kernel source-monotonic and journal-monotonic clocks also differ by about0.968
seconds and must not be mixed without calibration. Original observations remain
unaltered, with corrections in the separate analysis receipt.

The successful window had 1,014 common dxg `-22` messages and no completion-wait or
`-512` errors. That further excludes `-22` alone as a reliable failure signature.
Analysis receipt SHA256:
`fe34e698fae75cecbb3082c3a36ff0bfc642cabd29ddc176e0c174b30ced2d1b`.
Actual output is retained under
`runs/verification-gap-closure/assets-v1/diagnostics/ticket101-20261116T181923Z-d67100ed/`.

## Windows-side inspection and remaining diagnostic scope

Read-only host inspection found driver621.14 and Windows
`C:\WINDOWS\system32\nvidia-smi.exe`; the WSL kernel is
`6.18.58.1-microsoft-standard-WSL2`. An idle Windows query returned the same GPU UUID
and whole-device memory fields. This does not establish its reliability under load.
System event queries for Display, nvlddmkm and WHEA found no matching events during
17:45–18:25 UTC. The DxgKrnl query failed with a log/provider mismatch and parameter
error; its empty result is not evidence that no DxgKrnl events occurred.

NVIDIA documents limitations in WSL NVML support, including utilization and active
compute-process queries, in its [CUDA on WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/).
That is background context, not a diagnosis of these five-second failures.

A Windows-side observational comparison is being prepared with explicit Windows
process ownership and the same five-second query deadline. All existing Linux
guards must remain active. Preparation and harmless process-ownership checks are
CPU-only; a further GPU diagnostic requires review of that concrete preparation.
No driver reset/update, WSL restart, monitor replacement, stale-reading fallback,
query serialization or timeout relaxation has been performed or accepted.
