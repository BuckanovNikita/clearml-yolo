# Bug Assessment: Ctrl+C leaves GPU processes alive

- **Slug**: ctrl-c-gpu-orphans (generated from the report)
- **Created**: 2026-10-13
- **Source**: conversation
- **Verdict**: valid
- **Severity**: high — cancellation can strand GPU work and block queued jobs.

## Report

> Ok i identify that stopping on ctrl c not full kill processes and they still own gpus

The report concerns another multi-GPU machine. Its exact platform/version and signal
sequence are unavailable; local GPU inventory is irrelevant to this report.

## Symptom and reproduction

Two real CPU subprocess reproductions on 2026-10-13 established defects without
requiring GPUs or ClearML. A worker spawning a detached child with
`start_new_session=True` left that child alive after `cancel_process` returned
successfully. Separately, SIGINT during cancellation of a TERM-ignoring worker
raised KeyboardInterrupt while the worker remained alive. All reproduction-owned
processes were explicitly killed and reaped afterward. These establish code defects,
not which defect occurred on the user's host.

## Root cause and inspected code

`entrypoints/hydra/execution.py` retains only the worker process group and verifies
only that group. Installed Torch elastic's SubprocessHandler starts DDP ranks in
new sessions. Ultralytics launches torchrun using subprocess.run, whose exceptional
exit kills the immediate launcher, potentially orphaning ranks. The supervisor also
allows repeated signals to interrupt its bounded cleanup before ticket closure.
`worker.py` owns the live worker claim; `gpu_queue.py` correctly retains reservations
while a supervisor or worker lock remains held. No registry reset is appropriate.

## Proposed remediation

Add a stdlib runtime process-ownership adapter for Linux: a unique private inherited
launch marker plus PID/start-time identities finds detached and reparented native
children. Check identities when signalling; use pidfds on Linux. Continue bounded
cleanup and fail clearly on unresolved owned process visibility. Preserve Windows
Job Object supervision and the existing fallback on other POSIX platforms.
Defer SIGINT/SIGTERM during bounded cleanup, restore handlers afterward and preserve
cancellation outcomes. Discover new descendants before confirming cleanup complete.
Keep the queue schema, admission, GPU telemetry and native training interfaces intact.

**Files likely to change**: `src/clearml_yolo/adapters/runtime/process_tree.py`,
`src/clearml_yolo/entrypoints/hydra/execution.py`, `tests/test_gpu_cancellation.py`,
`docs/runtime-isolation.md`, `specs/022-simple-gpu-wait/contracts/execution.md`.

**Tests**: real detached/reparented child cleanup, actual repeated SIGINT with worker
claim/ticket release, unrelated process survival, signal restoration, denied owned
visibility and PID identity protection. Reuse existing queue, launcher, supervision,
CPU DDP and architecture checks. No dependency changes or upstream patches.

## Architecture and task ledger

See [architecture.json](architecture.json). Runtime owns OS inspection/signalling;
Hydra owns launch and lease ordering. Neither imports model SDKs. Existing import
contracts and negative architecture tests cover both modules.

- [x] Investigate and reproduce independently of remote GPU hardware.
- [ ] Validate architecture planning before implementation.
- [ ] Add failing regression tests, then implement the bounded cleanup fix.
- [ ] Run regression, static analysis, architecture and documentation checks.
- [ ] Obtain fresh independent review after parent integration/verification.
- [ ] Reconcile architecture acceptance and record fix/verification outcomes.
- [ ] Follow applicable commit/release workflow; preserve unrelated dirty changes.

Investigation ran in parallel with the parent's reproduction. Implementation follows
this record; regression tests can proceed with exclusive test-file ownership. Parent
integration/verification precedes fresh independent read-only review.

## Risks and limits

The original remote multi-GPU workload is unavailable. CPU process tests establish
lifecycle behavior, not remote GPU or ClearML publication. Marker discovery assumes
native children retain their inherited environment (as the inspected Torch launcher
does). Inaccessible relevant /proc state prevents verified release. No global process
name kills, queue deletion or unrelated process signalling is permitted.

## Release continuation

The user subsequently requested release of this fix. See [release.md](release.md)
for isolated scope, native verification and final release evidence. Earlier observations
and deferred-release entries above are retained as historical evidence.
