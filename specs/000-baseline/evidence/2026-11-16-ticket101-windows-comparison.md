# Ticket101 Windows comparison failure analysis — 2026-11-16

Read-only analysis of combined run `windows-comparison-20261116T185354Z-524e785d`
and native output `ticket101-20261116T185355Z-0dd1164d`. No new GPU query, allocation,
helper edit or retry. The [paired JSON](2026-11-16-ticket101-windows-comparison.json) binds the retained files and independently
rechecks all375 execution-manifest inputs; no bound source changed.

The host path had an actual timed-out process, not merely a delayed receipt for a
successful command. Windows query22, PID321588, was created18:54:23.637491Z. Its
independent five-second timer called TerminateProcess at18:54:28.656697Z; exit124,
`timeout_terminated`, empty stdout/stderr and cleanup=true were retained. The
entry finished18:54:29.773423Z, and the supervisor failed normally with cleanup=true
at18:54:29.808612Z. The timer action was about5.019s after process creation; the
whole entry took6.142s on Windows Stopwatch. These are process/supervision times,
not internal NVML measurements.

The retained Windows-minus-Linux UTC interval is[-0.077978,+0.428824] seconds.
Under that calibration:

| Event | Time or interval in Linux UTC |
| --- | --- |
| Windows query22 creation | 18:54:23.208667–23.715469 |
| Windows timer termination call | 18:54:28.227873–28.734675 |
| Conservative seven-second sample-age threshold | 18:54:29.186473 |
| Coordinator native SIGTERM | 18:54:29.221130 |
| Windows query entry finish | 18:54:29.344599–29.851401 |

The Windows timer action precedes native cancellation by at least0.486s across
the entire calibration interval. At cancellation, the oldest possible age of the
last successful host reading was7.034657s. The stale guard therefore acted on an
expired reading; it did not refresh age from delayed receipt publication.

Three Linux processes were sampled in `D`/disk-sleep with
`wchan=dxgvmb_send_sync_msg`: native-probe GPU query2314563, harness compute-PID
query2314565 and outer full GPU query2314588. Their wait snapshots overlap the
guaranteed pre-timer host-process lifetime18:54:23.715469–28.227873. Corrected
maximum sampled process ages in that wait state are5.262s,5.254s and4.119s,
respectively. Raw epoch ages retain the previously identified approximately0.819s
bias. Ages and sparse snapshots do not establish continuous wait duration.

The outer Linux query was cancelled before its own five-second deadline; this run
is not another reproduction of the original outer TimeoutExpired. There is no
successful host query demonstrated during this Linux wait interval. Both the
Windows/UNC path and Linux monitoring path became delayed.

The native rank file reports8/5warmup/10measured/1validation success, but the
enclosing native invocation was interrupted and no trial-result.json exists.
Its rank JSON mtime is18:54:29.201452, about19.7ms before SIGTERM; the observer first
saw it29.223084, about2ms after. This does not resolve the atomic publication order
more precisely or accept the cancelled invocation. The log was buffered until
that boundary, leaving the exact training/validation/cleanup phase unknown.

There were22 valid host samples, minimum16798MiB free, and22 valid outer Linux
samples, minimum16290MiB. No observed reserve breach occurred. The largest gap
between completed Linux samples was1.576s; that excludes the cancelled trailing
query and is not a continuous telemetry claim.

The kernel window contains507 common `-22` messages and nine completion-wait,
packet or `-512` messages. The latter begin approximately2ms after native SIGTERM
in journal realtime and cluster around subsequent worker interruption. This is
consistent with interruption consequences; it does not establish the cause of
the preceding delay. Kernel source-monotonic timestamps remain a separate clock
domain and are not substituted for the calibrated journal timestamps.

Windows cancellation returned “The parameter is incorrect.” The supervisor's
normal failure/exit overlaps the cancellation helper's bootstrap, making an
already-exited-target race plausible. The exact failing Win32 call/time is not
logged. The controller conservatively skipped its later Windows identity check
after cancellation failure and retained cleanup=unresolved. That original receipt
remains unchanged. Root subsequently proved all24 recorded Windows identities
absent, no Windows nonce/directory matches, no surviving recorded Linux identities
and an empty compute list. Later cleanup is resolved separately; the diagnostic
remains failed. Root post-cleanup SHA256:
`8f4f0c21a0a2d1ff68f80b71e7713b17a46740ee7d8e096fb6e4698f9ef3fdd3`.

This comparison does not isolate a WSL-only or host-driver cause. Windows output,
receipts and helper/compiler I/O used WSL-backed UNC storage. The empty output
cannot distinguish an internal query wait from blocked or buffered output.
The useful next CPU-only preparation is the separately owned Windows-local NTFS
variant: local helper/compiler/stdout/stderr/receipts, identical Job Object and
five-second timer, unchanged Linux guards, and post-window copy/hash handoff.
Harmless ownership/cleanup verification and review precede any separate live slot.
Even that variant's CLI elapsed time would not be internal NVML timing. No monitor,
reserve, deadline, driver or WSL change is justified by this result.

Companion analysis SHA256:
`8dafb42e76551e30a2611b10c0efc3bd575982cb9a79a5d225526214e5ffb311`.


The follow-up read-only DxgKrnl channel discovery succeeded: Diagnostic,
Performance, Power and Contention were disabled Analytical channels; Admin and
Operational were unavailable. No enabled channel was available for the retained
17:45–18:25 UTC window. This is a logging-availability limitation, not proof of
absence of GPU resets or stalls. No channel, ETW session or host setting changed.
The discovery's owned Windows identity was independently confirmed absent.

Verification disposition: the combined live diagnostic **failed**; native and
Windows process cleanup **passed on later independent observation**; exact
underlying cause and full GPU matrix continuation remain **deferred**. No code
fix, driver intervention, timeout relaxation or successful native acceptance is
established. Existing CY product tests and queue CPU pairing remain reusable
because this evidence-only change leaves their source and dependency inputs
unchanged. The canonical documentation route applies to this dated record.
