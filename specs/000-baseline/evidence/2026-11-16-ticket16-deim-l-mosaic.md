# Ticket16 DEIMv2 L JSON mosaic execution and readback — 2026-11-16

Status: accepted within the native ticket16 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket16-deim-l-mosaic.json) binds retained receipts and inventories; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the GPU run and cleanup; a separate agent executed CPU readback. Independent review reconciled retained observations. This dated-record task made no live calls or test executions.

## Inputs and execution

Actual launch source was `657edda357539fb6640533ca3de557c5f91f5970`. All 459 launch source hashes and 238 readback product hashes match ticket15, as do the lock, launcher, asset bindings, fixture, owner and native source identity. The unchanged source/fixture/helper review was reused. CPU preparation `ticket16-20261116T203222Z-c15b8ea6` passed at source `15e47f2`; fresh admission and actual launch `ticket16-20261116T204908Z-5d4b5460` bound the current source, WSL boot and `cy-it-ded7c4` service identity. The original five-second query timeout, 10 GiB reserve and two-epoch limit remained unchanged.

The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The paired JSON separately binds the manifest file bytes. Registered L-family initialization and initial optimizer-parameter hashes match the ticket14/15 baseline.

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-l-json_mosaic-690b57305f` passed in 199.907630 seconds; outer launcher elapsed time was 203.312036 seconds, exit 0. Fresh forced estimation passed batch 8, reached allocator OOM at batch 16 and reconfirmed batch 8. Both successful probes recorded five warmup steps, ten measured AdamW steps and one validation step. Peak observations were 15,755,640,832 and 15,751,446,528 bytes. Capacity applies to the admitted allocator budget and tested batches.

Training completed epochs 0 and 1 at batch 8, FP32, seed 0 and size 640: 40 optimizer updates, zero skipped updates and changed parameters. All 96 native epoch losses and 186 remote scalar losses were finite. The producer field `verification.native_loss_values` contains the 186 scalar observations, while readback's same-named field contains the 96 native epoch values; each was reconciled with its corresponding log. Native epoch validation completed.

The applied JSON recipe snapshot is `049739959eebe7b4291c3b22a4d56b9eb3b105e277f0c422a5d956a89ec353ff`: 2×2 Mosaic at 640, HorizontalFlip and RandomBrightnessContrast, each with probability 1. Snapshot, canonical/native recipe and unchanged executed adapter agree. Additional native mosaic/mixup/copyblend were disabled. No separate per-image mosaic trace is claimed.

All 196 outer telemetry samples met the 10,240 MiB reserve and user's 8 GiB floor. Minimum free VRAM was 10,362 MiB; maximum completed sample gap was 1.088057 seconds. No outer query timeout occurred. This establishes sampled observations, not continuous reserve, playback frame times or the historical WSL hang cause.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket16` produced task `df167ebc6ad74de79934650794dc59cc` and Output Model `fb0b6253e6ed48c4a8aeda4b0018609e`. Checkpoint SHA256 is `9ea4699d8aa3a6828ca266e510a2e9f417a692ac6e60d166546d89f54b19f2bf`. Fresh readback `readback/20261116T205320Z-1f9589b3` passed from 20:53:20 to 20:53:59 UTC with the unchanged reviewed helper.

Eight enabled artifacts and checkpoint bytes were forced through a fresh SDK cache, then independently rehashed. Task/model identity, configuration, thresholds and checkpoint metadata agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint and processed 40 validation images, including 15 backgrounds, yielding 12,000 detections. Exact-threshold scoring totals were TP 0, FP 1, FN 64. This is execution/publication evidence, not scientific accuracy, separate upstream solver validation or export parity.

## Protected cleanup and remaining scope

Independent review found no blocker. Launcher/worker cleanup passed. At cleanup, known ticket16 launcher, pytest, scenario and CPU readback PIDs were absent, and the exact-case process scan was empty. Ticket17 was independently running; no global compute-empty claim is made.

The coordinator rehashed 116 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,346,284 logical bytes.
- Successful readback `cache`: 9 files, 538,064,280 logical bytes.

The passed cleanup receipt records 562,410,564 logical bytes removed. Every checkpoint, retained artifact, CPU prediction, native input/log, receipt, fixture, shared asset, prior case and service was preserved. Ticket17 files and processes were untouched. Physical filesystem reclaim was not separately attributed.

Selected preparation, admission, training, measured capacity, mosaic recipe, source applicability, publication, CPU prediction/scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy and export compilation/runtime parity remain separate work. The historical WSL hang cause remains unproven, and earlier failed campaign attempts retain their status.
