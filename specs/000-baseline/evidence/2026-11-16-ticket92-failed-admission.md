# Ticket92: fresh admission failed before queue submission

On 2026-11-16, the coordinator launched the reviewed completed-case controller in
its exclusive serial GPU slot. The native estimator rejected the required batch72.
No queue job was submitted, no worker started, and no queued pipeline training or
publication occurred. Ticket92's live execution/lifecycle/readback checks remain
deferred; this attempt does not establish a new usable capacity, including64.

The [structured receipt](2026-11-16-ticket92-failed-admission.json) retains source,
environment, configuration and observer hashes, all native trials, actual failure
receipts and local log hashes. The [admission log](2026-11-16-ticket92-failed-admission.txt)
shows the helper refusing submission. Original evidence remains under
`runs/verification-gap-closure/assets-v1/queue-acceptance-v1/completed`.

## Inputs and actual phase

The paired environment was prepared at CY c026a75 and launched from its
documentation-only successor `137079d099490e2153405f042befe8325e9a38bc`; queue
remained `d3627a0da85968429ddeaff4920c05825e6e05e2`. Native package identity was
`dc64b31bce77b4949514befb3b1e2dfcc1178b3272ffe2f216204b72175379d9`.
The unchanged direct-baseline profile, frozen fixture/workload, two optimizer
paths and 8 GiB reserve were measured with a native search ceiling of72. The
controller ran at nice19/idle I/O priority with two-thread library environments.
This attempt began during the explicitly authorized video period.

| Trial | Native result |
| --- | --- |
| 8, 16, 48, 56 | Successful discovery measurements |
| 72 | Confirmed CUDA allocator OOM; requested142 MiB exceeded the process allowance |
| 64 | Successful discovery measurement |
| 64, fresh winner confirmation | Contaminated: free memory fell below8589934592 bytes |

The final case status is `failed`, with both `global_batch` and `per_gpu_batch`
null. The exact final diagnostic is:

> Fresh winner confirmation failed: GPU 0 free memory fell below the required reserve of 8589934592 bytes

The case's initial conservative occupancy was6317670400 bytes and post-case
occupancy5925502976 bytes. The lower post-case reading does not invalidate the
observed in-trial reserve breach. A successful discovery measurement at64 is not
an independent confirmed capacity; no capacity maximum is claimed.

## Fail-closed outcome and cleanup

The native admission process exited1. Its owned pool reports
`cleanup_complete=true`, `poll_cleanup_complete=true` and `interrupted=false`.
The controller finished with `status=failed`, `job_id=null`, no worker/monitor
exit values and `cleanup_complete=true`. Its failure is
`Fresh batch72 admission failed; submission is forbidden`.

Read-only checks of the retained controller and admission PID/start identities
found neither identity alive. The queue-descendant receipt is empty because no
queue execution started; it is not an independent inventory of all probe GPU
processes. The coordinator subsequently confirmed an empty whole-device compute-process list
and the controller PID absent before releasing the slot to ticket08. That GPU
check was performed by the coordinator; this evidence author did not repeat it.
No reservation was administratively cleared and no unrelated process was signalled.

The accepted direct batch72 baseline remains intact. There is no smaller-batch
fallback, automatic rerun or automatic new direct baseline. A later queue attempt
requires an explicitly scheduled fresh admission under suitable resource conditions
or a reviewed matching direct baseline within the authorized campaign scope. Completed-result readback tooling
may be prepared on CPU, but this failed case cannot pass its local admission gate.

The frozen controller SHA-256 is
`da79ec617444ade7448c327e8086d90bf533560e4193e2cc14dc8a99c50c5d5e`;
its admission helper SHA-256 is
`c05014e159f042c53fd9ab5e5f7dbfc450f3e65849f1ee6b0a324abcf3ce9033`.
The paired environment and failed-case receipts/logs are retained intentionally.
No controller, monitor, worker or admission process remains owned by this attempt;
no queue coordination binding or metadata root was created. Separate CPU-only
readback-tool preparation does not modify these frozen execution inputs.
