# Native verification — 2026-10-13

Available native checks and tagged cleanup are complete. This record distinguishes
executed checks, retained failures and unavailable required targets. The earlier failure evidence remains in
[the pre-refactor baseline](baseline-2026-10-13.md).

## First integrated baseline

The actual `cy` pipeline completed successfully on one physical GPU: training,
prediction, validation calibration, train/val/test evaluation, comparison without
an automatic baseline, and required uploads. The command exited zero and the
ClearML task reached `completed`. One hundred native training epochs ran with
image size 64, batch 2, workers 0, AMP disabled, eager execution and seed 0. The
input was one fixed local checkpoint and 16 distinct images: eight train, four
validation and four test, including a background image in each split. Prediction
used image size 64, batch 2, confidence 0.001 and maximum 30 detections.

Source identity:
`d1c20234a4b65b954cbd2f7e05ff68dca69a53be602fa6169b5f32254e10bcf6`.
All 171 Python source files and their hashes were retained before subsequent
review-driven changes. The successful baseline task was
`2b6e124e05e4465bb9af8b204b222049` in the explicitly tagged acceptance project.

An independent process read the remote API every approximately 0.5 seconds;
it did not initialize a task. Across 880 polls, 752 observed `in_progress` and
551 observed native training still active. It matched 1,405 native scalar
events while the task was active, including 1,386 while training continued.
The worst matched observed visibility delay was 2.288 seconds, with zero API
errors. These delays measure first local journal observation to first independent
remote observation; they are sampled measurements rather than server receipt
timestamps. This historical observer stamped a poll before making the remote
API request, so the reported delays do not include that request's duration. They
are retained with this measurement limit and do not establish the corrected
response-completion method used by the final matrix. Native console lines were
also read during execution. The append-only
stdout, stderr and scalar journals, remote events and timestamps remain retained.

The application was traced with `strace -ff -ttt -e trace=%file`. The tracer's
library path was supplied only to the tracer and removed from the application
environment, preserving the application's original selectors. File-write
classification and paired numerical readback were completed later, as recorded below.

Force-download readback found eleven artifacts and one native best Output Model.
The canonical GT contains all sixteen images and original source fields, with sixteen
unique generated source-row IDs. Producer row ordering is normalized, so preservation
was compared by image identity. Prediction/evaluation contexts contain train/val/test
and a separate comparison-candidate test context. The downloaded best checkpoint
hash equals both the retained native checkpoint and its fresh server model metadata;
the recorded calibration also identifies that checkpoint and the validation split.

The traced application used ordinary user Ultralytics settings through read-only
opens. No queue modules or host-local queue namespace accesses appeared in the
direct `cy` trace. Library-internal policies remain unchanged: ClearML cache/locks,
CUDA ComputeCache, openpyxl worksheet scratch and filelock import capability probes
can write outside the project. In particular, openpyxl's `create_temporary_file()`
selects its own default tempfile directory when its `WorksheetWriter` receives no
explicit output; the application selects a contained final workbook path. These are
third-party scratch policies preserved by the approved plan, not application-selected
external workbook destinations. No global tempfile, HOME or XDG selector was changed.

Review identified possible cleanup of fork-only children and sibling-output
containment gaps before the next pipeline. The matrix orchestrator was paused
without interrupting its native baseline child. Once the pipeline, publisher and
mirror exited, production changes were released to the parent. This baseline
therefore establishes the recorded source identity; it does not accept the
subsequently revised source.

## Subsequent direct run and finalization diagnostic

The next full direct eager pipeline ran twenty epochs against source identity
`7b899490fdc02b8c79445e11b2dfacbe7bccb795eff7258b09cef448b1cd1bf4`,
with the same checkpoint, image size, batch, AMP, seed and prediction settings.
Training, prediction, validation calibration, paired baseline/current-test comparison,
developer/business reports, seventeen artifact uploads and native best-model publication
completed. Task `fa9a7bc5add44c12973576a64dc46373` then failed during owner
finalization; the actual native command exited one. Its original traceback ends in
`TaskFinalizationError: ClearML task finalization deadline expired`, after
`Task.close()` waited in the installed SDK reporter's multiprocessing synchronization.
This is a separate failure from the earlier compiled model-publication `missing id`
exception. The matrix orchestrator was interrupted only after the native command
had exited; its exit 130 is not the native command's exit status. No queued matrix
case was launched against this source. Force-download readback retained all seventeen
artifacts and the single best model despite the failed task status. The downloaded
checkpoint matches the retained native checkpoint and fresh server model/calibration
metadata; validation thresholds match the downloaded threshold CSV exactly. All sixteen
input images, original fields and unique generated source-row IDs are preserved.

A separately labelled real-SDK CPU diagnostic used the retained immutable source,
a real owner task and console publisher, artifact/model reporting and the ordinary
SDK policy. It performed no GPU computation. Test-only instrumentation recorded
scope exclusion identities, ownership scans, signal requests, task-close boundaries
and owner/reporter stacks; process, signal and file syscalls were traced. Every
native ownership scan returned an empty owned set and the existing SDK reporter
remained excluded and alive. There is no observed scope signal to a reporter in
these reproductions.

With the unchanged fifteen-second production deadline, diagnostic task
`7f50d986ce5f4f28af391156ea4477b3` failed with the same finalization exception
and exited one. Finalization spent 9.413 seconds before entering `Task.close()`,
leaving 5.589 seconds for that call before the shared deadline interrupted it.
A separate sixty-second diagnostic, task `495a271c96b8460ab4f04d7830edf821`,
completed and exited zero: 9.436 seconds preceded `Task.close()`, which then took
9.907 seconds, for approximately 19.343 seconds overall. The larger deadline was
an explicit diagnostic comparison, not an environment-wide workaround or proof
that every possible synchronization failure is resolved.

At three seconds into the successful close, the owner stack showed
`Task.flush()` → `Reporter.wait_for_events()` → `ForkEvent.wait()`; the reporter
was alive in its report-service, resource/status and log-monitor waits. The installed
SDK flushes inside `Task.close()` as well as during application finalization. These
observations support an insufficient shared deadline for the observed two drainage
phases. They do not support the earlier hypothesis that native cleanup killed the
SDK reporter. The failure trace and successful diagnostic stacks remain retained
separately. A later production budget change requires fresh direct/queued acceptance
without the diagnostic override.

Both diagnostic owners, SDK reporters, output mirrors and publishers exited and
were reaped; their exact recorded PID identities were absent on the cleanup check.
The prior matrix/native/observer identities were also absent. These diagnostics
preceded the successful revised matrix below.

## Final candidate measurement

The final matrix records source identity
`2d3b90a79f774ce44a8320c2a71e3078ff661f5fd07509be34c66ce69693b624`
for all 172 retained Python files. Both direct and queued eager pipelines completed
with zero native exit, completed remote tasks and absent recorded descendants.
The direct and queued compiled pipelines subsequently also completed with zero
native exit, completed remote tasks, seventeen artifacts and one best model each.
Corrected independent observations matched 285 scalar events while each task was
active, including 266 while eager training continued and 272 while compiled training
continued. Worst observed delays were 2.234, 2.243, 2.239 and 2.238 seconds for
direct eager, queued eager, direct compiled and queued compiled respectively, with
zero API errors. Default compiler threading was used; the earlier missing-ID failure
was not reproduced, which does not establish a causal fix.

After the queued eager terminal boundary, the worker and orchestrator were reaped;
remaining phases import the identical retained source through `PYTHONPATH`. Queue
snapshot fingerprint validation remains enabled. A later production-only change to
`adapters/storage/native_archive.py` validates archive destinations and generated ZIP
leaves before creation, while preserving serialization and archive contents. That
correction requires its own actual ZIP containment/content regression evidence; this
matrix must not be described as executing the later guard.

The final matrix records independent
console and scalar API response-completion timestamps. Its visibility checks must
match emitted events while the task is `in_progress` and native training remains
active, with healthy-service delay at most ten seconds. The active-task child
console case additionally embeds its actual production timestamp and unique marker
in real FD output. Logs produced before a task exists are labelled separately;
their eventual visibility is not evidence of active-task delivery latency. Earlier
request-start observations remain historical evidence with the limitation above.

The active-task child case emitted a unique timestamped marker through real
`os.write` calls on stdout and stderr, including a partial stdout line and its
completion. An independent API read observed these while native training and the
remote task were both active, 1.634 seconds after the child production timestamp.
The full pipeline completed. A separate pre-epoch case retained the child's partial
stdout/completion and stderr, then failed with the original native Ultralytics
`NotImplementedError` for the intentionally invalid optimizer; its nonzero exit was
expected. Those child emissions preceded task creation and are not a live-task
latency measurement.

## Readback, inference parity and CPU distributed transport

Force-download readback of the baseline and all four matching matrix tasks verified
the required artifact inventories and a single native best model per training task.
Fresh checkpoint and calibration hashes agree, validation threshold metadata equals
the canonical CSV exactly, test thresholds remain frozen, and strict threshold flags
agree with raw confidence values. All original sixteen-image source fields and unique
generated row IDs are preserved. Direct/queued prediction tables contain 181 rows
for each mode after normalizing producer roles; the maximum numerical difference
is exactly zero for both eager and compiled pairs.

Quiet application inference was compared with actual verbose native inference using
the same checkpoint, sixteen images, batch, image size and normal confidence 0.001.
Both paths processed all sixteen images and returned eighty nonempty detections,
with numerical parity within `1e-6`; no parity-only zero-confidence fallback was
needed. Task `3468a044954b4c11908853a0f79da783` completed and its parity artifact
was force-downloaded; standalone inference produced no Output Model. An initial
harness attempt accidentally passed the reserved `source=None` setting, failed, and
was retained separately before correcting that test-only argument.

An additional real two-rank CPU/Gloo run used the existing test accelerator adapters
and actual optimizer/trainer, distributed samplers and DistributedDataParallel. It
used a genuine owner task and publisher, not a recording task. Both ranks completed
two epochs on CPU with CUDA uninitialized. An independent remote reader matched
four epoch-zero native metrics while both workers remained at their telemetry gate;
the worst response-completion delay was 1.647 seconds. The gate then released and
both workers exited. Task `e26a48f4b556435b842424c1e8cc7b92` completed; its
transport evidence and one native best Output Model were force-downloaded. This
establishes the real owner-to-remote scalar path for CPU-adapted distributed training;
it does not establish physical multi-GPU acceptance or model quality.

## Cancellation and publisher failures before correction

Actual direct repeated Ctrl+C targeted only the verified owner after native GPU
training began, with two forked data workers. It exited nonzero, retained diagnostics,
left no recorded descendants, and the remote task reached `failed`.

Queue repeated cancellation, forced worker death, forced guardian death, blocked
followers and explicit recovery were executed on the immutable matrix source.
Reservations persisted while the original guardian/native tree was live or recovery
was uncertain; followers remained pending, then ran after verified cleanup. Recorded
PID/birth identities were absent when capacity released. The normal queue cancellation
reached remote `stopped`, with the final SDK stop warning present, but complete remote
console readback lacked the original signal/secondary cleanup exception preserved
locally. This was a final-publication gap, despite correct process/capacity cleanup.

Stopping a verified task-owned publisher with SIGSTOP and killing it during an
original native optimizer failure both exposed a required failure: the owner exited
by SIGKILL and the remote task became `stopped`, rather than `failed`. The stopped
publisher case exited 109.33 seconds after injection; local logs retain the barrier
exception. The combined case retains the original optimizer exception locally, but
it was absent from the complete remote console. Installed SDK source identifies the
observed status-change warning and subsequent self-kill in its development monitor;
these cases are recorded as acceptance failures, not successful fault tests. All
284 recorded fault/lifecycle PID identities were absent at the cleanup checkpoint.

## Filesystem observation and later source corrections

The filesystem audit covers the success matrix, earlier diagnostics and
pre-correction lifecycle traces. Every successful write-capable/path-changing
file syscall in that audit was classified, including both absolute source/destination
paths. All 85 relative `unlinkat` paths were resolved
from preceding directory-FD opens: 51 project paths and 34 library capability-probe
paths. No successful application-selected write outside resolved `CY_HOME` was
observed. Other writes follow preserved installed SDK/library policy: ClearML edit
locks/cache, CUDA ComputeCache, openpyxl worksheet scratch, standard-library temporary
directory/multiprocessing probes, filelock probes and native Tcl import scratch.
Failed creation/open attempts are recorded separately as having no filesystem effect.
The raw initial classification, resolved paths and installed-source callsites remain
retained. File-path tracing observes destinations and write-capable opens; it does
not measure every byte written or replace invalid/symlink destination regressions.
Additional corrected-replay traces are retained separately; the completed classification
is not asserted to cover those later traces.

Later production corrections affect four files relative to the matrix source:
`adapters/storage/native_archive.py`, `adapters/queue/guardian.py`,
`adapters/clearml/session.py` and `adapters/clearml/deadline.py`. They add archive
leaf validation, owner-first cancellation grace, incomplete-owner protection and
bounded failed-owner/SDK callback cleanup. The matching success matrix above did not
execute those later changes. Their focused corrected native replay uses a distinct
172-file immutable source identity:
`ce15b8cdaa58cf479885a8428f5c1b229fff8ac720fe0efa88c088c5ac418a42`.

## Corrected focused native replays

The corrected source above completed an actual stopped-publisher case and a
killed-publisher case combined with the original invalid-optimizer failure. Both
owners exited nonzero, their independently reloaded remote tasks reached `failed`,
and neither printed the SDK self-abort warning. The first barrier-to-owner-exit
intervals were 9.882 seconds and 1.830 seconds respectively; full command duration
includes setup/training and is not the failure-handling interval. Local append-only
logs preserve the original exceptions and publication failures. Complete remote
readback contains 53 and one console events respectively, without the original
exceptions: a failed console channel cannot establish delivery of those diagnostics.
This remaining delivery limitation is distinct from failed status and retained local
logs.

The stopped-publisher case also reproduced the original ClearML SDK model
publication `ValueError: Failed reloading Model: missing id` during an eager run.
Its full native/SDK traceback remains preserved separately. This combined failure
cannot establish a publisher-only fault. A separately labelled stopped-publisher
replay completed the full native pipeline with 17 artifacts and one best model, then
failed only on the console barrier deadline. Its owner exited 10.143 seconds after
the first barrier started and its remote task reached `failed`, with no SDK
self-abort, manual cleanup or recorded survivors. Injection-to-wrapper-exit took
105.677 seconds because the pipeline continued computing/reporting before reaching
the barrier; this is not the failure-handling interval. All 17 artifacts and the
best model were force-downloaded despite the expected failed task. Its complete
remote console contains 57 events emitted before the stopped channel ceased delivery,
and lacks the final barrier exception retained locally. The four ordinary success-matrix pipelines did not
reproduce this intermittent SDK failure; their successes do not resolve it.

Corrected repeated queue cancellation reached remote `failed` and released capacity
16.977 seconds after cancellation. Complete independent readback of task
`712f35b49d7e474baaad04cfec7d2f10` contains 80 console events, including both
`Invocation failed ... _SignalExit: 143` and the original signal traceback. It lacks
the SDK self-abort warning. This directly verifies the owner-first grace correction
against the earlier remote-final-diagnostic gap.

Two legitimate successful SDK owners ran sequentially in the same process. Tasks
`0bd34c121cac47a0b0e44191288744ec` and
`ac367326998e4e32a68547953fd6f4af` independently reached `completed` in
16.808 and 17.594 seconds. After each actual close, the public
`task.is_main_task()` returned false and `Task.current_task()` was clear. The tasks
have distinct IDs. The original failed cases are retained; no retry overwrites them.

Later error-preservation corrections in `adapters/clearml/session.py`,
`adapters/observability/diagnostics.py` and `entrypoints/hydra/common.py` protect
the original exception when cleanup, a Loguru sink or its stderr fallback fails.
The closure-source replays above do not execute those later guards; their real-sink
and interruption regressions and final source checks are recorded by the parent
workflow. They do not alter native computation settings or queue allocation.

## Final cleanup and acceptance limits

Independent final process verification found all 307 recorded PID/birth identities
and six additional sequential-SDK child birth identities absent. All eight queue
jobs are terminal and no task-owned physical GPU claim remains. Corrected-case
remote statuses, complete console events and every available artifact/model were
read back independently before tag-scoped cleanup. The original model-ID failure
has no remote artifact or Output Model; its native best checkpoint and full local
trace remain retained. Invocation arenas, immutable sources and downloaded evidence
are intentionally retained locally.

Tag-scoped ClearML cleanup exited successfully and independently listed zero
projects and zero tasks under the exact run tag. Only the owned project/tasks were
deleted; retained local evidence and normal SDK caches were left intact.

Five-GPU eager/compiled execution, physical multi-GPU DDP, two-host NFS and
two-user acceptance are unavailable. The user confirmed that no additional target
environment is available; no substitute environment or account creation is requested.
They remain unverified
gates; single-device execution and simulated protocol tests do not establish them.
The earlier compiled `missing id` model-publication failure and intermittent CPU-DDP
SIGILL evidence must not be overwritten by successful later runs.

Detailed commands, source snapshots, PID identities, GPU mappings, memory samples,
raw traces and API events are retained in the ignored task-owned evidence area.
No shared service or pre-existing workload was stopped or modified.

## Release reconciliation cancellation replay

The later user-directed release uncovered missing published v0.26.2 process-tree
safeguards in the refactor's starting copy. Their restoration changes only
`adapters/runtime/process_tree.py` from the preceding final software checkpoint.
The [release record](release-2026-10-13.md) preserves the new exact 172-file manifest,
red/green regressions and repeated real one-GPU direct/queued cancellation evidence.
Both affected cancellation paths passed on that immutable source; all 13 recorded
process identities and owned GPU claims were gone, and tagged remote resources
were removed. The full matrix above retains its original source scope and the
unavailable native targets and unresolved native failures remain open.
