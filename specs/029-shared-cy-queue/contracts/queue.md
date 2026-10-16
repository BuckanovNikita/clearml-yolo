# Command and ownership contract

`cy` and existing stage commands run directly. Removed queue/autogpu overrides fail
with guidance to use cy-queue; `cy -m` is sequential.

`cy-queue submit (--gpus N | --devices 0,2) -- [cy overrides]` submits resolved immutable
jobs. `-- -m ...` expands and validates all jobs before committing any. `worker` serves
only the effective Unix user, with disjoint allocations concurrently. `list`, `move`,
`cancel`, `recover`, and optional `tui` use the application interface. Move supports
up/down/top/bottom/before/after and expected revision. Foreign hosts are view-only.
Only owners cancel/recover; all local participants reorder pending jobs.

Configuration amendment, 2026-10-16: queue locations now require an absolute shared
`CY_QUEUE_CONFIG` TOML path, with explicit metadata and host-local coordination roots.
There is no project fallback; `--root` overrides metadata and legacy `CY_QUEUE_ROOT`
must agree. See the [current settings/archive interfaces](../../034-readable-shared-queue/contracts/interfaces.md).
Owner files are private; summaries
and actor reorder events are public. No credentials in summaries. CUDA bindings are
set before fresh execution; all training devices and first inference device are
selected, while explicit CPU phases remain CPU. Compile/AMP/batch/model settings stay
unchanged. Training retains the full allocation until the guardian durably shrinks it
to the first GPU, releases extras and acknowledges the handoff. No notification keeps
the full allocation; failed/lost acknowledgement stops inference without restoring
released extras. Unless explicitly freed, retain the first GPU through pipeline and
owned descendant exit.

## Current-generation capacity amendment — 2026-10-15

Current reservations and operator holds exclude GPUs across roots. Stale unlocked
records alone do not veto admission. Explicit per-device free advances its generation,
fences older guardians and preserves sibling reservations, running processes and job
outcomes. Every new job still requires fresh used VRAM strictly below 2 GiB (2048 MiB).
A completed ClearML task, verified process cleanup and available GPU are separate facts;
uncertain outcomes require owner recovery and are never retried automatically.
The [queue guide](../../../docs/queue.md) owns operations and the
[lifecycle diagram](../../../docs/queue-lifecycles.md) separates these state machines.
