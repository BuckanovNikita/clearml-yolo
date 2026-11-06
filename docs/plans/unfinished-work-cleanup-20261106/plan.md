# Unfinished work consolidation — 2026-11-06

## Purpose

Before the 2026-11-06 consolidation, every unfinished CY change lived uncommitted in
separate worktrees: the closure, force, repair and sequential checkouts. This task
collects that work on master so new work starts from one clean state. The user
selected **merge without release**. No version bump, tag or native GPU execution is
part of this task.

## Sources and selection

| Source | Base | Outcome |
| --- | --- | --- |
| Sequential integration (`work/sequential-integration-20261105`) | 0.45.1 | Primary source. All runtime and test changes are applied unchanged on top of master `43de5af`: force, DINOv3 HF weights, scoped campaign and accelerator-OOM. |
| Closure integration (`work/closure-20261104`) | 0.45.0 | Dated records that were not ported are added: the 004 native closeout, the 006 speedup comparison and review, T041/T044, and the historical yolo-weights and yolo-numerical-search delivery receipts. |
| Closure integration, campaign record | 0.45.0 | `docs/bugs/campaign-20261102/` is added as an **open** bug record. Scoped campaign improvements cover only part of it. |
| Closure integration, force/DINOv3 records | 0.45.0 | The sequential versions supersede them. The 2026-11-04 force verification is kept as a historical section. Its earlier `accepted` statuses are not restored, because the sequential port reset acceptance to pending. |
| Closure proposed CY | 0.45.0 | Its 0.46.0 version and lock bump are dropped, because no release is made. |
| Closure campaign/dinov3/force, force source, repair checkout | 0.44.8–0.45.0 | Earlier copies of the same streams. They contain nothing beyond the sources above. |

Before applying anything, each worktree's diff and untracked files were snapshotted
outside the repository.

Completion claims were checked against retained receipts before they were carried
forward:
- The 004 checkpoint hashes match the default-HF archive manifest.
- The v0.44.2 and v0.44.3 release commits match their local tags.
- The speedup timings cite the retained benchmark review.

## Architecture

Impact: none for this consolidation. See the [record](architecture.json). Runtime
modules, interfaces and import contracts are owned by the existing records:
- [force](../../../specs/006-batch-training/force/architecture.json)
- [DINOv3 HF](../../bugs/dinov3-hf-native/architecture.json)
- [scoped campaign](../../bugs/campaign-scoped-improvements/architecture.json)
- [accelerator OOM](../../bugs/accelerator-oom-receipts/architecture.json)

This task adds no source beyond those records.

## Open gates (unchanged by this task)

- Forced selected DEIM L/X estimator confirmation and the complete 64-model forced
  catalogue (006 T064).
- Native accelerator-OOM replay. The separate L telemetry failure (helper exit 255,
  bounded telemetry timeout) is unresolved.
- The original campaign's numerical failures, the SIGILL investigation and the full
  20-case recovery.
- Physical multi-GPU acceptance.
- Proposed-version CY/queue pairing, the fresh final review and Git-only release
  (006 T063/T065).

## Verification

Recorded in [verification.md](verification.md).
