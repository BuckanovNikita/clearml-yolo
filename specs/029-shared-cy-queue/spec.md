# Feature Specification: Direct execution and shared cy-queue

Date: 2026-10-13. Status: implementation requested. Source: user-approved refactor plan.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run directly with explicit devices (Priority: P1)

As a pipeline user I run cy or any stage command with native devices, without queue
storage, GPU discovery, reservations, workers, waiting, or Textual. Ordinary Hydra
multiruns execute sequentially. Application-owned outputs, caches, logs and scratch
stay beneath the resolved project root; external inputs and normal SDK paths remain valid.
Acceptance: fresh-process import isolation, native-settings preservation, legacy-control
migration errors, and pre-write containment including symlink escapes.

### User Story 2 - Collaborate through a durable queue (Priority: P1)

As a Unix user I submit jobs, close my terminal, and run my own persistent worker.
Other participants may reorder pending jobs, but only I execute/cancel/change/resubmit
mine. Jobs return stable IDs and expose public summaries without private configurations.
Each host orders independently and selects the earliest runnable job, skipping absent
workers and unavailable whole allocations. Training holds the full allocation; an
acknowledged post-training handoff releases all except the first inference GPU. The
remaining reservation lasts through pipeline/descendant exit.
Acceptance: concurrent claim/move/cancel, stale-view rejection, user ownership, distinct
host queues, and host-global UUID exclusion across roots and mount aliases.

### User Story 3 - Observe and cancel native execution (Priority: P1)

As an operator I see child/native output and epoch metrics while training is active,
retain full local logs after failure, and cancel without stranding ranks or freeing
capacity prematurely. Prediction shows one operation progress indicator and a summary.
Acceptance: independent live remote reads within ten seconds under healthy service,
FD/partial-line capture, failure before epoch one, bounded publisher failure/shutdown,
repeated cancellation, worker/guardian death and verified owner recovery.

### Edge Cases

Unknown protocols, corrupt committed records, NFS interruption, restrictive ownership,
inaccessible process evidence, PID reuse, detached ranks, boot changes and incompatible
active versions stop admission. Expired heartbeat, missing parent, or low GPU memory
never prove cleanup. Uncertain execution is never automatically retried. Shared queue
metadata alone may escape the project; local coordination holds small records only.

## Requirements *(mandatory)*

### Functional Requirements

- FR-01: Direct commands execute configured native devices with no queue imports or effects.
- FR-02: Remove four-mode queue/autogpu controls and default queue launcher; reject legacy controls with migration guidance. Keep sequential cy -m.
- FR-03: cy-queue exposes submit, worker, tui, list, move, cancel and recover. TUI is optional and closing it leaves workers alive.
- FR-04: Submit accepts mutually exclusive --gpus N / --devices ordered indexes; validate and expand the whole Hydra sweep before committing submissions.
- FR-05: Immutable private snapshots retain resolved config, cwd/project, interpreter/package identity, request and order; revalidate compatibility before launch. Credentials use owner environment.
- FR-06: Allocation sets CUDA_VISIBLE_DEVICES before a fresh process, binds all train devices and first inference device, preserves explicit CPU phases and other native settings, and rejects conflicting overrides.
- FR-07: CY_QUEUE_ROOT defaults inside project; durable NFS records partition by stable host with separate boot identity. Foreign hosts are view-only.
- FR-08: Effective UID and filesystem ownership govern execution/cancellation; each actor owns append-only reorder events. Serialize revisions and reject stale views.
- FR-09: Earliest runnable scheduling skips unavailable owners/resources; one worker per owner/root supports disjoint concurrent jobs. Atomically reserve all UUIDs globally across queue roots.
- FR-10: Same-user guardian owns locks and scoped subreaper supervision outside job ClearML finalization; persist guardian claim before launch gate. Worker death cannot release allocation. After native training returns and unused model memory is released, durably shrink to the first GPU, release extras and update public allocation before bounded acknowledgement. No training-finished notification retains the full allocation. Failure after durable shrink does not restore released extras; cleanup/recovery follows the remaining durable claim.
- FR-11: Cancellation reaps complete owned descendants, retaining PID/start-time, marker and pidfd protections. Unrelated same-UID process access denials do not poison scoped live guardian discovery. Guardian death or uncertain cleanup requires owner recovery and quarantines capacity across roots; recovery retains conservative global ownership proof. Supervisor cleanup uncertainty does not retroactively fail a successful completed ClearML task; required computation/publication failures still fail.
- FR-12: Fail closed on unsupported Linux coordination, NFS failure, damaged state, unknown protocols or incompatible active versions. Never infer cleanup from liveness or memory alone.
- FR-13: Constrain application writes before creation, including Hydra, explicit outputs/cache/scratch and symlinks; preserve SDK policies, outside inputs and old data.
- FR-14: Capture stdout/stderr at FD boundary into project append-only logs; unbuffered output and terminal mirror remain independent of remote publication.
- FR-15: Supervised publisher attaches existing task without lifecycle ownership, batches approximately every two seconds, isolates diagnostics, preserves DDP scalar relay, and drains to final offsets with a deadline.
- FR-16: Retain local logs, fail incomplete required publication, preserve original exceptions and avoid automatic replay of uncertain deliveries.
- FR-17: Prediction verbose=false independent of training; all backends, standalone/pipeline/comparison share one progress operation, no ordinary per-image lines, warnings/errors/final summary retained, aggregate output rate limited.
- FR-18: Preserve unfinished cancellation work and v0.26.1 history; investigate five-GPU compiler failure and intermittent CPU-DDP SIGILL separately without claiming retries or scheduling resolve them.

### Key Entities *(include if feature involves data)*

ResourceRequest, JobSnapshot, PublicJob, OrderingEvent, WorkerIdentity, GuardianClaim,
GPUObservation, ExecutionRecord, ConsoleOffset and publication receipt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

All functional requirements pass executable acceptance. Direct versus queued execution
matches on one and five physical GPUs in eager and compiled modes. Two actual Unix users
and two hosts sharing NFS satisfy ownership/partition rules. Healthy-service console and
produced epoch metrics are remotely visible within ten seconds while training is active.
Prediction covers identical images with identical numerical results. Full pytest, Ruff,
mypy, Vulture, import-linter, architecture negative cases, docs/links/examples and fresh
installed distributions pass. Missing infrastructure/native failures remain acceptance gaps.

## Assumptions

Cooperating Linux users, consistent NFS UID mapping and shared host PID/local-lock namespace;
no privileged services, account creation, mount changes or deletion of live lock files.
Admission memory thresholds are not capacity guarantees. The 2026-10-15 user amendment
requires post-training allocation contraction and external guardian finalization; this
supersedes the original whole-pipeline reservation assumption without changing archived
implementation evidence.
The explicit user plan supersedes historical constitution prohibitions on daemon/count/
reorder controls; installed workflow files and completed historical evidence remain unchanged.
