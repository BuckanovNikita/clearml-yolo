# Ticket102: Queue lifecycle observation diagnosis

Status: diagnosis complete; correction and required pairing verification pending.
This blocks ticket92 v3 preparation, not unrelated direct backend/export work.
No queue product code, dependency pin, installed environment or scientific tolerance
was changed by this diagnosis. The isolated test-correction owner has exclusive
use of the retained v3 interpreter after the completed suite cleanup.

## Evidence and exact scope

Both newly failed runs used queue `d3627a0da85968429ddeaff4920c05825e6e05e2`.
Selected native pairing ran against clean managed CY
`ba56e2f2751954fb9c65799817d22b9e51b36b89`; its metadata, installation,
static checks and import checks passed before unit failures. Queue source was clean.
The accompanying JSON binds the precise source files, logs and retained public
records, together with the full ticket100 preparation receipt.

| Execution | Result | Retained evidence |
| --- | --- | --- |
| Historical native pairing, CY60b5c63, same queue pin | 527 passed, 7 deselected, 136.20s | `.tmp/verification-gap-closure/ticket92-pair-20261116/paired-check.log` |
| New maintained native Task | 3 failed, 524 passed, 7 deselected, 181.56s | `ticket92-plan-v3-20261116/native-paired-check.log` |
| Actual retained v3 interpreter | 2 failed, 525 passed, 7 deselected, 179.74s | `ticket92-plan-v3-20261116/queue-tests.log` |

The latter two paths are beneath `.tmp/verification-gap-closure/`.
All five failure observations and both temporary test trees are retained.
The historical pass cannot supersede these failures. No unmodified retry was used
to make either failed suite appear successful.

## Cancellation publication and capacity release

`tests/test_guardian_grace.py:183`,
`test_cancellation_keeps_publishers_alive_and_capacity_owned_through_final_logs`,
failed in the native Task: the public state was cancelled while the test immediately
observed GPU-a/GPU-b reservations. The helper waits for public cancellation, then
asserts release without waiting for that separate observation.

`src/cy_queue/adapters/queue/guardian.py:352` publishes the terminal outcome before
line355 calls `lease.release_verified()`. Maintained `specs/baseline.md:100` states
that job completion alone never proves capacity release; `docs/interfaces.md:93–96`
explicitly retains guardian cleanup/publication/release ownership and permits a
terminal record with a dead retained claim to require recovery. Thus terminal state
is not an atomic release guarantee. No physical GPU leak or unauthorized cleanup
is established by this controlled-device test observation.

A bounded wait for verified reservation release is consistent with that contract,
provided owner/descendant identity, their actual exit, final publication and the
release assertion are retained. Replacing the assertion with a delay or accepting
uncertain cleanup would not establish the requirement.

## Startup refusal and diagnostic publication

`tests/test_queue_admission.py:57`,
`test_guardian_rechecks_memory_before_workload_exec`, failed for native parameters
`[None-2.0]`, `[0-12.0]` and actual-v3 parameters `[None-12.0]`, `[0-2.0]`.
All four observations saw pending revision2 with `waiting_reason=None`.

`guardian.py:257–262` releases the rejected startup lease, publishes pending, then
writes the waiting reason in a separate storage transaction. `runtime.py:272–275`
returns when the public state leaves starting; it does not wait for that later
reason write. `storage.py:set_waiting` separately updates the reason and revision.
All four retained failed public records subsequently reached pending revision3
with exactly the expected unavailable/at-least-threshold reason. The companion
JSON retains each job ID, reason, path and hash.

The maintained requirements demand refusal for unknown or threshold-reaching
memory and a displayed wait reason. No requirement for atomic pending/reason
co-publication or a ready reason at `start()` return was found in the baseline,
interfaces and public usage contracts. The observed sequence therefore supports a
test observation race; it does not demonstrate workload admission on unsafe memory.
A bounded poll for the exact expected reason must retain assertions that the
workload did not start and that the eventual diagnostic is correct.

## Ownership, limits and next verification

The test subprocesses use controlled device metadata and do not prove live GPU
reserve behavior. CPU-only preparation used CUDA hidden, nice19 and two CPUs.
Every supervised child was reaped; final supervisor/test PIDs1036372/1036373 and
928901/928903 were absent. A bounded `/proc` scan found no remaining command
containing the owned v3 path before interpreter handoff. Native Task removed its
own temporary environment. Test evidence and private caches remain intentionally
retained; no durable queue coordination state was removed.

The unchanged source ordering, actual intermediate records and maintained contract
support a test-only correction. Parent assigned that work in an isolated queue
worktree at the same revision. Independent review, affected test verification and
a fresh selected paired gate remain required; no corrected result is claimed here.
The original queue checkout, dependency pins and failed v2 scientific status remain
unchanged. Ticket100's exact CPU pixel equality is independent evidence and does
not establish solved native direct/queued scientific parity.
