# Ordinary YOLO OOM retry defect — 2026-11-15

Discovered while implementing ticket03; tracked separately as [ticket94](../../../.scratch/verification-gap-closure/issues/94-prevent-hidden-yolo-oom-retries.md).
The existing [batch-estimation contract](../../../docs/batch-estimation.md) requires training OOM to fail without automatic retry or hidden batch reduction.

Read-only inspection of installed Ultralytics8.4.184 `ultralytics/engine/trainer.py`, lines495 and567–639, shows an initial retry counter, first-epoch single-GPU memory-error handling, batch halving and pipeline rebuild, with up to three retries. File SHA-256: `7d060019b31e85ec429c16b7e728e9d7c5a9083b497fc2b362a76a543808dc60`.
No installed upstream files were edited.

Ticket03 introduces a scoped strict acceptance recipe that rejects batch changes and repeated epochs. That protects its own runs, but ordinary product behavior deliberately remains unchanged until ticket94. This is a source-backed contract mismatch, not fresh physical GPU OOM evidence. The future fix must reproduce the CY failure path with a bounded injected error before correcting it; actual GPU exhaustion is not required to risk the reserved memory. No runtime claim or acceptance is recorded here.
