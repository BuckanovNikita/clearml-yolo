# Ticket101 Windows-local diagnostic — 2026-11-16

The first Windows-local comparison **failed after the native single-batch probe passed**.
Process cleanup and evidence retention passed. This is a diagnostic result; ticket15,
the full GPU matrix and the underlying telemetry cause remain unresolved.
The [companion receipt](2026-11-16-ticket101-windows-local.json) binds the archived
preparation, independent reviews, live receipts and analysis of121 retained files.

## Reviewed preparation

Independent review initially blocked the candidate on two cleanup gaps. Revision3
moved potentially blocking evidence copy/hash I/O into an owned Linux worker with a
60second supervisor wait. Native cleanup allows10seconds, direct reap3seconds and
the enclosing native scope may use another10seconds. Timeout, worker error or
unresolved cleanup prevents approval to delete the Windows-local evidence.

Manual CPU proof covered a normal copy, a blocked FIFO open and a hash mismatch.
The1second blocked-open deadline returned after1.054seconds with the child reaped;
failed cases produced no completion approval. This does not simulate an unkillable
kernel I/O task. Renewed harmless Windows normal-exit,5second timeout and Job Object
close checks passed;14 files were retained and hash-verified before exact owned
nonce-directory deletion.

Revision3 also keeps an auxiliary Windows cancellation failure unresolved even when
subsequent primary identities are absent. Primary inspection continues, global
cleanup stays incomplete and local evidence remains. That branch was reviewed by
source control flow; no new live auxiliary-error injection was claimed.

Fresh independent review rehashed14 preparation,384 execution,10 original,20 archived
candidate and14 retained-file bindings, plus3 check logs, and compared15 unchanged
AST blocks. All matched. All3 original Linux guards,10GiB reserve,5second Windows
timer,7second last-sample bound,12second readiness and75second total bound remained.
The reviewed revision3 files now have immutable snapshots under `windows-local-pre-r4`;
later preparation edits cannot change this proof.

## Live outcome

Execution used source `50c32e78f5278df07b59f5e123832666ba9f1eb1` and WSL boot
`5e9f68d1-63db-4188-9995-e686745fda8c`. Fresh admission observed29105MiB free,
an empty compute list and successful bounded telemetry queries. Windows helper,
compiler scratch, current directory, outputs and receipts used the owned NTFS root.
Linux continued reading those receipts through its Windows filesystem mapping.

Combined run `windows-local-comparison-20261116T200005Z-90ad1405` started20:00:05.640926Z.
Native output `ticket101-20261116T200008Z-8965c3ae` completed batch8 with5 warmup,
10 measured and1 validation steps in25.716seconds. The native worker wrapper recorded
30.749seconds, exit0 and cleanup complete; its observer had no errors or survivors.
The coordinator observed native completion at20:00:42.804670Z and continued finishing
the bounded Windows observation stream. The native diagnostic was not cancelled.

The controller then raised PermissionError errno13 opening `observer/receipt.json`.
Its exact timestamp was not logged; it occurred after the last admitted receipt at
20:00:47.315973Z and before the cancelled observer wait completed20:00:48.639917Z.
There were38 admitted host samples and30 outer Linux samples, both with minimum
18059MiB free. The longest admitted host process/supervision interval was0.074565seconds;
maximum calibrated oldest-sample age at consumption was0.876135seconds. The largest
completed Linux sample gap was1.094911seconds. No slow/deadline-adjacent SMI snapshot
was recorded. These are sampled observations, not internal NVML timings or continuous
reserve proof.

The retained Windows receipt contains39 completed entries. Case38 was not admitted
before failure and is retrospective evidence only. The supervisor receipt remains
running because the controller cancelled it. Its60second stream did not complete;
the combined diagnostic remains failed despite the successful native probe.

## Cleanup and interpretation

All40 exact Windows identities were absent and all3 owned Linux slots confirmed
cleanup. The supervised transfer retained86 hash-verified files, then removed its
exact Windows nonce directory. A separate coordinator postcheck rehashed those86
files, confirmed5 outer/coordinator/transfer PIDs absent and an empty compute list.
A later check confirmed all139 recorded native process PIDs absent. Failure logs,
receipts and retained copies remain available.

The original Windows publisher uses in-place Set-Content. A transient sharing/access
conflict is consistent with this denial and the later successful cleanup reads, but
no Win32 sharing-violation code or handle trace proves that cause. WSL restart and
Windows-local output placement both changed since the earlier UNC run; this attempt
cannot identify which changed the telemetry behavior. It recorded no recurrence of
the earlier5second query timeout, which is not proof that the cause is fixed.

At that point, a narrow optional-receipt correction was proposed; its later reviewed
execution is recorded separately below: PermissionError
may mean unavailable data, without adding a sample or refreshing its timestamp. The
existing7second stale-data,12second readiness and75second overall limits must continue;
strict final reads must remain strict. CPU deny/recover and stale-data proof plus
fresh review precede any separate live attempt. This failed attempt must remain intact.

Native documentation consistency against the bound receipts passed. The final project
gate belongs to the coordinator after committing this dated evidence. Existing product
checks remain reusable because product sources and dependencies are unchanged. No
full training, physical multi-GPU, export parity, queue parity, release or deployment
outcome is claimed.

## Separate revision4 attempt: writer publication conflict

Revision4 changed only the optional `partial` read to treat PermissionError as
unavailable data, without refreshing a sample. Independent review verified20 preparation,
388 execution,10 original and29 archived bindings plus3 check logs; the other18
function/class AST blocks remained unchanged. Simulated CPU denial/recovery preserved
samples, accepted ages1.0/6.9seconds and rejected7.1seconds; strict final reads and
unrelated I/O errors still failed. The original guards and deadlines remained intact.

The separate run `windows-local-comparison-20261116T200707Z-172b9729` failed at the
Windows writer. Its retained receipt records System.IO.IOException because receipt.json
was in use by another process, with FileSystemProvider.ClearContent in the stack.
The original in-place Set-Content publication failed. This establishes a writer-side
sharing/access conflict; the competing process/handle was not identified. Concurrent
Linux polling is plausible, but is not proven to be that holder. The preceding
revision3 reader denial cannot be assigned this exact cause retrospectively.

The host final failure/cleanup timestamp20:07:24.911466Z maps to Linux
20:07:24.416315–24.951254Z under the retained clock bracket. Native SIGTERM at
20:07:25.008623Z therefore followed by at least57.369ms. The native probe at
`ticket101-20261116T200709Z-60b7d25b` was interrupted and has no trial result;
this attempt has no accepted native outcome. This does not alter the prior
revision3 native pass.

There were15 completed host samples and one incomplete query record. The admitted
host samples had minimum28280MiB free, maximum process/supervision interval0.071957seconds
and maximum oldest age0.602312seconds. The14 Linux readings had minimum28278MiB
free and maximum completed-sample gap1.078552seconds. No slow/deadline-adjacent SMI
snapshot or five-second query timeout was recorded. The incomplete query has no
completion/timer outcome and is not accepted telemetry.

Cleanup passed:17 exact Windows identities were absent,40 retained files were
hash-verified and the owned Windows directory was removed. Root independently
confirmed all72 recorded Linux PIDs absent and an empty compute list. The revision4
analysis binds72 retained files. Its reviewed preparation has immutable snapshots
under `windows-local-pre-r5`; both failed attempts and their receipts remain intact.

The optional reader correction alone was insufficient. Further GPU execution is
**deferred** until receipt publication passes representative concurrent Windows-writer/
Linux-reader CPU proof, ownership/retention/failure checks and independent review.
No driver, WSL or historical telemetry-root-cause fix is established. The prior
revision3 failure, revision3 native success, revision4 publication failure and revision4
native cancellation remain separate outcomes.
