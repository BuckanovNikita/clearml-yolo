# Command and ownership contract

`cy` and existing stage commands run directly. Removed queue/autogpu overrides fail
with guidance to use cy-queue; `cy -m` is sequential.

`cy-queue submit (--gpus N | --devices 0,2) -- [cy overrides]` submits resolved immutable
jobs. `-- -m ...` expands and validates all jobs before committing any. `worker` serves
only the effective Unix user, with disjoint allocations concurrently. `list`, `move`,
`cancel`, `recover`, and optional `tui` use the application interface. Move supports
up/down/top/bottom/before/after and expected revision. Foreign hosts are view-only.
Only owners cancel/recover; all local participants reorder pending jobs.

Queue roots use CY_QUEUE_ROOT or project/.cy-queue. Owner files are private; summaries
and actor reorder events are public. No credentials in summaries. CUDA bindings are
set before fresh execution; all training devices and first inference device are
selected, while explicit CPU phases remain CPU. Compile/AMP/batch/model settings stay
unchanged. Retain allocation until entire pipeline and descendants exit.
