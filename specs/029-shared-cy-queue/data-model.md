# Queue data and transitions

Resource requests contain either a positive count or unique ordered physical UUIDs.
Private immutable snapshots contain resolved pipeline configuration, project/cwd,
interpreter and package fingerprint; credentials remain in owner environment.
Public summaries contain ID, effective UID, host, submission sequence, state, request,
allocation, wait reason, progress and task link without executable configuration.
Actor-owned order events carry global revision, actor UID and affected IDs. Revision
checks serialize concurrent reorder, claim and cancel under a host-local transaction lock.

Pending -> starting -> running -> completed/failed/cancelled, or recovery_required
when cleanup/outcome is uncertain. Only verified owner recovery resolves that job uncertainty.
Cancel pending is terminal; cancel active requests guardian cleanup. Running jobs never
move/preempt. Guardian claims contain boot, PID/start-time, marker and GPU UUIDs; local
claims retain recovery evidence after lock-owner death. Current-generation reservations
exclude capacity across roots; stale unlocked records alone do not. Per-device generation
advancement fences earlier guardian writes without changing the job outcome. See the
[current contract](contracts/queue.md#current-generation-capacity-amendment--2026-10-15).
