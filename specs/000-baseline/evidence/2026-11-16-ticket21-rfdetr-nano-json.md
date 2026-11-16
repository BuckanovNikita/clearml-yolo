# Ticket21 RF-DETR nano JSON execution and readback — 2026-11-16

Status: accepted within the native ticket21 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket21-rfdetr-nano-json.json) binds retained receipts; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed GPU training and cleanup; a separate agent executed CPU readback. Independent review reconciled RF-specific native configuration, CSV and JSON recipe. This dated-record task made no live calls or test executions.

## Inputs and execution

Actual launch source was `657edda357539fb6640533ca3de557c5f91f5970`. All 459 launch source hashes and 238 readback source hashes match ticket15. Unchanged shared source/fixture review and ticket20's RF helper/precision review were reused. CPU preparation `ticket21-20261116T212046Z-88bb2bc2` and its fresh admission passed. Actual launch evidence is `ticket21-20261116T212356Z-61fbde57`, bound to environment `cy-it-ded7c4`. The five-second query timeout, 10 GiB reserve and two-epoch limit remained unchanged.

The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The paired JSON separately binds manifest file bytes. Rehashed registered RF nano initialization and initial optimizer-parameter SHA256 `a45679bd5c1cc935475000d0a3524115b2ad22229d86e7a80ca1cbc31b8b8d6e` match the accepted ticket20 baseline. No DEIM-family parameter comparison was used.

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/rfdetr-nano-json-5475fc405e` passed in 209.236655 seconds; outer launcher elapsed time was 212.015501 seconds, exit 0. Fresh forced estimation passed batches 8, 16 and 24, reached allocator OOM at 32 and reconfirmed 24. Successful probes each completed five warmup steps, ten measured AdamW steps and one validation step. Batch 24 peaks were 20,756,299,776 and 20,757,348,352 bytes. Nominal and effective probe sizes are both 384; capacity applies to the admitted allocator budget and this custom recipe.

Two epochs completed at batch 24 and seed 0, with 14 optimizer updates, zero skips and changed parameters. The update count follows 2 × ceil(160 / 24); native CSV steps are 6 and 13, with train/validation losses for both epochs. Execution is FP32 through native `amp_dtype=null`; the saved model-config AMP default does not determine Lightning execution precision.

All 34 native CSV loss values and 42 remote scalar losses are finite and reconcile with their corresponding logs. These are distinct populations; the producer field `verification.native_loss_values` contains scalar observations. Native CSV bytes match exactly, and independent CSV parsing agrees with the pandas receipt within absolute tolerance 1e-14. Native RF epoch validation completed.

JSON snapshot `bfdd9c00d36be4d222068553563e91dcde506316a6b78751cfe45e769f975e09` contains HorizontalFlip and RandomBrightnessContrast, each with probability 1. Snapshot, canonical/native recipe and unchanged executed adapter agree. Overlapping RF native augmentation is disabled: empty aug_config, torchvision augmentation backend, scale_jitter false and multi_scale off. No per-image transform trace is claimed.

All 203 outer telemetry samples met the 10,240 MiB reserve and user's 8 GiB floor. Minimum free VRAM was 12,780 MiB; maximum completed sample gap was 1.094054 seconds. No outer query timeout occurred. These are sampled observations, not continuous reserve, playback frame-time or historical WSL hang proof.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket21` produced task `6db7251cad4e4a4986bd3d93cb9c5415` and Output Model `e8f130dc214143a09cc21de07c86bc27`. The downloaded `checkpoint_best_total.pth` has SHA256 `2590b3df1675d1d7958be9638f8e7d03b7c2b59e93ef8da0a458861058f563af`. Fresh readback `readback/20261116T212814Z-97e80de2` passed from 21:28:14 to 21:28:29 UTC; local admission and remote executor sessions exited 0.

Eight enabled artifacts and checkpoint bytes were forced through a fresh SDK cache and independently rehashed. Task/model identity, configuration, thresholds, RF descriptor and native CSV agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint for 40 validation images, including 15 backgrounds, yielding 10,980 detections. Exact-threshold scoring totals were TP 12, FP 111, FN 52. This remains smoke execution/publication evidence, not scientific accuracy, separate upstream solver validation or CPU/GPU numerical parity.

## Protected cleanup and remaining scope

Independent review found no blocker. Launcher/worker cleanup passed. The first cleanup attempt refused an unreadable transient PID 2686006 before any deletion. The coordinator confirmed that PID absent and reran the unchanged helper successfully without adding an exclusion. The successful receipt records five known native/readback PIDs absent, exact-case and cache open-handle scans empty, with only the existing unrelated user systemd PID 340 and sd-pam PID 344 exclusions. No global compute-empty claim is made.

The coordinator rehashed 123 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,345,320 logical bytes.
- Successful readback `cache`: 9 files, 136,986,113 logical bytes.

The passed cleanup receipt records 161,331,433 logical bytes removed. Every checkpoint, retained artifact, CPU prediction, native input/log, receipt, RF initialization asset, fixture, prior case and service remained protected. Other ticket workloads were untouched. Physical filesystem reclaim was not separately attributed.

Selected preparation, admission, training, capacity, JSON recipe/precision, native CSV validation, initialization, source applicability, publication, CPU scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy and export compilation/runtime parity remain separate work. The historical WSL hang cause remains unproven and earlier failed campaign attempts retain their status.
